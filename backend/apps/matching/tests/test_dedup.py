"""T-008: dedup on enrollment completion flags duplicate persons (eager Celery)."""

import pytest

from apps.enrollment.services import complete_enrollment
from apps.matching.models import MatchJob

from .helpers import enroll_person

pytestmark = pytest.mark.django_db


class TestDedup:
    def test_duplicate_person_flagged(self):
        # Person A is already enrolled with image #100.
        enrollment_a, record_a = enroll_person(100)
        complete_enrollment(enrollment_a)

        # Person B enrolls with the SAME biometric image → must be flagged.
        enrollment_b, _ = enroll_person(100)
        result = complete_enrollment(enrollment_b)

        job = MatchJob.objects.get(id=result["dedup_job_id"])
        assert job.job_type == MatchJob.JobType.DEDUP
        assert job.status == MatchJob.Status.DONE  # eager Celery ran inline
        assert job.probe_enrollment_id == enrollment_b.id

        candidates = list(job.candidates.all())
        assert len(candidates) == 1
        top = candidates[0]
        assert top.person_id == enrollment_a.person_id  # the duplicate identity
        assert top.record_id == record_a.id
        assert top.score == 100.0
        assert top.rank == 1

    def test_unique_person_produces_no_candidates(self):
        enrollment_a, _ = enroll_person(200)
        complete_enrollment(enrollment_a)

        enrollment_b, _ = enroll_person(201)  # different biometrics
        result = complete_enrollment(enrollment_b)

        job = MatchJob.objects.get(id=result["dedup_job_id"])
        assert job.status == MatchJob.Status.DONE
        assert job.candidates.count() == 0

    def test_dedup_aggregates_to_one_candidate_per_person(self):
        # Person A enrolled twice with the same image → two matching records,
        # but dedup must surface person A once (best record).
        enrollment_a1, _ = enroll_person(300)
        complete_enrollment(enrollment_a1)
        enrollment_a2, _ = enroll_person(300, person=enrollment_a1.person, position="2")
        complete_enrollment(enrollment_a2)

        enrollment_b, _ = enroll_person(300)  # same image, new person
        result = complete_enrollment(enrollment_b)

        job = MatchJob.objects.get(id=result["dedup_job_id"])
        person_ids = [c.person_id for c in job.candidates.all()]
        assert person_ids.count(enrollment_a1.person_id) == 1

    def test_dedup_requested_by_defaults_to_operator(self, make_user):
        operator = make_user("operator")
        enrollment, _ = enroll_person(400)
        enrollment.operator = operator
        enrollment.save(update_fields=["operator"])

        result = complete_enrollment(enrollment)
        job = MatchJob.objects.get(id=result["dedup_job_id"])
        assert job.requested_by_id == operator.id
