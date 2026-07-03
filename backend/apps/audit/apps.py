from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    verbose_name = "Audit & Logging"

    def ready(self) -> None:
        from .signals import connect_audited_models

        connect_audited_models()
