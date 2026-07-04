"""Walk an application through the status machine for clearance tests."""

from django.core.files.uploadedfile import SimpleUploadedFile

from apps.registration.models import ClearanceApplication
from apps.registration.services import Status, mark_paid, submit, transition
from apps.registration.tests.factories import ApplicationFactory


def application_in_state(status: str) -> ClearanceApplication:
    application = ApplicationFactory()
    application.id_document = SimpleUploadedFile("id.pdf", b"%PDF-1.4 x")
    application.save(update_fields=["id_document"])
    if status == Status.DRAFT:
        return application
    submit(application)
    if status == Status.SUBMITTED:
        return application
    mark_paid(application)
    if status == Status.PAID:
        return application
    transition(application, Status.BIOMETRICS_CAPTURED)
    if status == Status.BIOMETRICS_CAPTURED:
        return application
    transition(application, Status.IN_REVIEW)
    if status == Status.IN_REVIEW:
        return application
    transition(application, Status.APPROVED)
    return application
