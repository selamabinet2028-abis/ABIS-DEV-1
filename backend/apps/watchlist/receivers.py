from apps.matching.signals import match_job_completed

from .services import create_alerts_for_job


def on_match_job_completed(sender, job, **kwargs):
    create_alerts_for_job(job)


def connect_receivers() -> None:
    match_job_completed.connect(
        on_match_job_completed, dispatch_uid="watchlist:match_job_completed"
    )
