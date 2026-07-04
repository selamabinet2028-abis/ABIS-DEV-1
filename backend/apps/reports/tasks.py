from celery import shared_task


@shared_task(name="reports.run_report")
def run_report(run_id: str) -> str:
    from .models import ReportRun
    from .services import execute_run

    run = ReportRun.objects.select_related("definition").get(id=run_id)
    execute_run(run)
    return run.status
