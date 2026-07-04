from celery import shared_task


@shared_task(name="matching.run_match_job")
def run_match_job(job_id: str) -> str:
    from .models import MatchJob
    from .services import execute_job

    job = MatchJob.objects.get(id=job_id)
    execute_job(job)
    return job.status
