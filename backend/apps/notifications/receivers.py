from apps.registration.signals import application_status_changed

from .services import notify_application_status


def on_application_status_changed(
    sender, application, old_status, new_status, **kwargs
):
    notify_application_status(application, new_status)


def connect_receivers() -> None:
    application_status_changed.connect(
        on_application_status_changed,
        dispatch_uid="notifications:application_status_changed",
    )
