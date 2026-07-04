from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    verbose_name = "SMS & Notifications"

    def ready(self) -> None:
        from .receivers import connect_receivers

        connect_receivers()
