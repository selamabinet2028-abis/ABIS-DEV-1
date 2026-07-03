from django.apps import AppConfig


class BasedataConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.basedata"
    verbose_name = "Base Data"
