"""T-005: AuditLog is insert-only — update/delete raise at every level."""
import pytest

from apps.audit.models import AuditImmutabilityError, AuditLog
from apps.audit.services import write_audit

pytestmark = pytest.mark.django_db


@pytest.fixture
def log() -> AuditLog:
    return write_audit(AuditLog.Action.CREATE, entity="basedata.Person", entity_id="x-1")


def test_insert_is_allowed(log):
    assert AuditLog.objects.filter(id=log.id).exists()


def test_instance_save_after_insert_raises(log):
    log.action = AuditLog.Action.DELETE
    with pytest.raises(AuditImmutabilityError):
        log.save()


def test_instance_delete_raises(log):
    with pytest.raises(AuditImmutabilityError):
        log.delete()
    assert AuditLog.objects.filter(id=log.id).exists()


def test_queryset_update_raises(log):
    with pytest.raises(AuditImmutabilityError):
        AuditLog.objects.all().update(action=AuditLog.Action.DELETE)


def test_queryset_delete_raises(log):
    with pytest.raises(AuditImmutabilityError):
        AuditLog.objects.all().delete()
    assert AuditLog.objects.filter(id=log.id).exists()


def test_bulk_update_raises(log):
    log.action = AuditLog.Action.DELETE
    with pytest.raises(AuditImmutabilityError):
        AuditLog.objects.bulk_update([log], ["action"])
