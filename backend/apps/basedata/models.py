from django.db import models

from common.models import BaseModel


class OrgUnit(BaseModel):
    """Organizational unit hierarchy.

    Minimal at T-004 (User.org_unit FK needs it); full fields + CRUD land
    with T-006. Person, LookupValue, InvestigationCategory also arrive there.
    """

    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
