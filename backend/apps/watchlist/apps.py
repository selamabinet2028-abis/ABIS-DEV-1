from django.apps import AppConfig


class WatchlistConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.watchlist"
    verbose_name = "Watchlist Management"

    def ready(self) -> None:
        from .receivers import connect_receivers

        connect_receivers()
