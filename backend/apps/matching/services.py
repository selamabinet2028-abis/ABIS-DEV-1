"""Matching services — the only entry points other apps may import.

Public API: start_identify_job, start_dedup_job, verify_person_record,
execute_job (Celery), decide_candidate.
"""

from __future__ import annotations

from typing import Iterator

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.enrollment.models import (BiometricRecord, BiometricTemplate,
                                    Enrollment, Modality)
from apps.investigation.models import LatentPrint
from apps.preprocessing.crypto import decrypt_bytes

from .engines.base import get_engine
from .models import MatchCandidate, MatchJob

# Which record modality feeds each record-probed job type.
JOB_PROBE_MODALITY = {
    MatchJob.JobType.TP_TP: Modality.FINGER,
    MatchJob.JobType.TP_LT: Modality.FINGER,
    MatchJob.JobType.FACE_1N: Modality.FACE,
}

LATENT_JOB_TYPES = {MatchJob.JobType.LT_TP, MatchJob.JobType.LT_LT}


def default_threshold() -> float:
    return settings.ABIS_MATCH_THRESHOLD


def record_template(record: BiometricRecord) -> bytes | None:
    try:
        template = record.template
    except BiometricTemplate.DoesNotExist:
        return None
    return decrypt_bytes(bytes(template.template_bytes))


def _record_gallery(
    modality: str,
    *,
    exclude_record_ids: tuple = (),
    exclude_person_ids: tuple = (),
) -> Iterator[tuple[BiometricRecord, bytes]]:
    records = (
        BiometricRecord.objects.filter(
            accepted=True,
            modality=modality,
            template__isnull=False,
            person__is_deleted=False,
        )
        .exclude(id__in=exclude_record_ids)
        .exclude(person_id__in=exclude_person_ids)
        .select_related("template", "person")
    )
    for record in records.iterator():
        yield record, decrypt_bytes(bytes(record.template.template_bytes))


def latent_template(latent: LatentPrint) -> bytes:
    """Extract a template from the latent's working image (enhanced wins)."""
    engine = get_engine()
    field = latent.working_image_field()
    with field.open("rb") as fh:
        return engine.extract(fh.read())


def _latent_gallery(
    modality: str, *, exclude_latent_ids: tuple = ()
) -> Iterator[tuple[LatentPrint, bytes]]:
    latents = (
        LatentPrint.objects.filter(modality=modality)
        .exclude(id__in=exclude_latent_ids)
        .select_related("case")
    )
    for latent in latents.iterator():
        yield latent, latent_template(latent)


def _dispatch(job: MatchJob) -> None:
    from .tasks import run_match_job

    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        run_match_job.delay(
            str(job.id)
        )  # inline in tests — on_commit never fires there
    else:
        transaction.on_commit(lambda: run_match_job.delay(str(job.id)))


def start_identify_job(
    *,
    probe_record: BiometricRecord,
    job_type: str,
    threshold: float | None,
    requested_by,
) -> MatchJob:
    job = MatchJob.objects.create(
        job_type=job_type,
        probe_record=probe_record,
        threshold=threshold if threshold is not None else default_threshold(),
        requested_by=requested_by,
    )
    _dispatch(job)
    return job


def start_latent_search_job(
    *, latent: LatentPrint, job_type: str, threshold: float | None, requested_by
) -> MatchJob:
    """LT-TP / LT-LT launch — called by investigation views (documented API)."""
    job = MatchJob.objects.create(
        job_type=job_type,
        probe_latent=latent,
        threshold=threshold if threshold is not None else default_threshold(),
        requested_by=requested_by,
    )
    _dispatch(job)
    return job


def start_photo_search_job(
    *, photo_probe, threshold: float | None, requested_by
) -> MatchJob:
    """FACE-1N from an uploaded photo — called by pis views (documented API)."""
    job = MatchJob.objects.create(
        job_type=MatchJob.JobType.FACE_1N,
        probe_photo=photo_probe,
        threshold=threshold if threshold is not None else default_threshold(),
        requested_by=requested_by,
    )
    _dispatch(job)
    return job


def start_dedup_job(enrollment: Enrollment, *, requested_by=None) -> MatchJob:
    """Called by enrollment.services on completion (documented cross-app API)."""
    job = MatchJob.objects.create(
        job_type=MatchJob.JobType.DEDUP,
        probe_enrollment=enrollment,
        threshold=default_threshold(),
        requested_by=requested_by or enrollment.operator,
    )
    _dispatch(job)
    return job


def verify_person_record(
    *, person, record: BiometricRecord, requested_by
) -> tuple[MatchJob, bool, float]:
    """Synchronous 1:1 verification: record vs the person's stored templates."""
    engine = get_engine()
    probe = record_template(record)
    threshold = default_threshold()

    job = MatchJob.objects.create(
        job_type=MatchJob.JobType.VERIFY,
        probe_record=record,
        threshold=threshold,
        requested_by=requested_by,
        status=MatchJob.Status.RUNNING,
        started_at=timezone.now(),
    )

    best_score = 0.0
    matched = False
    if probe is not None:
        gallery = _record_gallery(record.modality, exclude_record_ids=(record.id,))
        person_items = [(r, t) for r, t in gallery if r.person_id == person.id]
        for _, template in person_items:
            ok, score = engine.verify(probe, template, threshold=threshold)
            if score > best_score:
                best_score, matched = score, ok

    job.status = MatchJob.Status.DONE
    job.finished_at = timezone.now()
    job.save(update_fields=["status", "finished_at"])
    return job, matched, round(best_score, 2)


def execute_job(job: MatchJob) -> None:
    """Celery entry point — runs one queued job to completion."""
    engine = get_engine()
    job.status = MatchJob.Status.RUNNING
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])

    try:
        if job.job_type == MatchJob.JobType.DEDUP:
            ranked = _run_dedup(engine, job)
        elif job.job_type == MatchJob.JobType.TP_LT:
            ranked = _run_tp_lt(engine, job)
        elif job.job_type == MatchJob.JobType.LT_TP:
            ranked = _run_lt_tp(engine, job)
        elif job.job_type == MatchJob.JobType.LT_LT:
            ranked = _run_lt_lt(engine, job)
        elif job.job_type in JOB_PROBE_MODALITY:
            ranked = _run_identify(engine, job)
        else:
            raise ValueError(f"Unsupported job type {job.job_type}")
    except Exception as exc:
        job.status = MatchJob.Status.FAILED
        job.error = str(exc)[:2000]
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "error", "finished_at"])
        return

    for rank, (target, score) in enumerate(ranked, start=1):
        if isinstance(target, LatentPrint):
            MatchCandidate.objects.create(
                job=job, latent=target, score=score, rank=rank
            )
        else:
            MatchCandidate.objects.create(
                job=job, person=target.person, record=target, score=score, rank=rank
            )

    job.status = MatchJob.Status.DONE
    job.finished_at = timezone.now()
    job.save(update_fields=["status", "finished_at"])


def _run_identify(engine, job: MatchJob) -> list[tuple[BiometricRecord, float]]:
    exclude_record_ids: tuple = ()
    if job.job_type == MatchJob.JobType.FACE_1N and job.probe_photo_id:
        # PIS photo probe (ADR-019): extract from the uploaded image.
        with job.probe_photo.image.open("rb") as fh:
            probe = engine.extract(fh.read())
    else:
        probe = record_template(job.probe_record)
        if probe is None:
            raise ValueError("Probe record has no template.")
        exclude_record_ids = (job.probe_record_id,)
    gallery = _record_gallery(
        JOB_PROBE_MODALITY[job.job_type], exclude_record_ids=exclude_record_ids
    )
    return engine.identify(
        probe, gallery, threshold=job.threshold, top_k=settings.ABIS_MATCH_TOP_K
    )


def _run_tp_lt(engine, job: MatchJob) -> list[tuple[LatentPrint, float]]:
    """Tenprint probe vs the unsolved latent file."""
    probe = record_template(job.probe_record)
    if probe is None:
        raise ValueError("Probe record has no template.")
    gallery = _latent_gallery(job.probe_record.modality)
    return engine.identify(
        probe, gallery, threshold=job.threshold, top_k=settings.ABIS_MATCH_TOP_K
    )


def _run_lt_tp(engine, job: MatchJob) -> list[tuple[BiometricRecord, float]]:
    """Latent probe vs the person database (same modality records)."""
    if job.probe_latent is None:
        raise ValueError("LT-TP job has no probe latent.")
    probe = latent_template(job.probe_latent)
    gallery = _record_gallery(job.probe_latent.modality)
    return engine.identify(
        probe, gallery, threshold=job.threshold, top_k=settings.ABIS_MATCH_TOP_K
    )


def _run_lt_lt(engine, job: MatchJob) -> list[tuple[LatentPrint, float]]:
    """Latent probe vs the other unsolved latents."""
    if job.probe_latent is None:
        raise ValueError("LT-LT job has no probe latent.")
    probe = latent_template(job.probe_latent)
    gallery = _latent_gallery(
        job.probe_latent.modality, exclude_latent_ids=(job.probe_latent_id,)
    )
    return engine.identify(
        probe, gallery, threshold=job.threshold, top_k=settings.ABIS_MATCH_TOP_K
    )


def _run_dedup(engine, job: MatchJob) -> list[tuple[BiometricRecord, float]]:
    """Person-level aggregation: best-scoring record per other person."""
    enrollment = job.probe_enrollment
    if enrollment is None:
        raise ValueError("DEDUP job has no probe enrollment.")

    best_by_person: dict = {}
    probe_records = enrollment.records.filter(accepted=True, template__isnull=False)
    for probe_record in probe_records.select_related("template"):
        probe = decrypt_bytes(bytes(probe_record.template.template_bytes))
        gallery = _record_gallery(
            probe_record.modality, exclude_person_ids=(enrollment.person_id,)
        )
        for record, score in engine.identify(
            probe, gallery, threshold=job.threshold, top_k=settings.ABIS_MATCH_TOP_K
        ):
            current = best_by_person.get(record.person_id)
            if current is None or score > current[1]:
                best_by_person[record.person_id] = (record, score)

    ranked = sorted(best_by_person.values(), key=lambda item: -item[1])
    return ranked[: settings.ABIS_MATCH_TOP_K]


def decide_candidate(
    candidate: MatchCandidate, *, decision: str, user
) -> MatchCandidate:
    candidate.decision = decision
    candidate.verified_by = user
    candidate.decided_at = timezone.now()
    candidate.save(update_fields=["decision", "verified_by", "decided_at"])
    return candidate
