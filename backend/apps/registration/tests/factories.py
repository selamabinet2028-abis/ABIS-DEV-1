import factory
from factory.django import DjangoModelFactory

from apps.basedata.tests.factories import PersonFactory
from apps.registration.models import ClearanceApplication


class ApplicationFactory(DjangoModelFactory):
    class Meta:
        model = ClearanceApplication

    person = factory.SubFactory(PersonFactory)
    purpose = "abroad_work"
