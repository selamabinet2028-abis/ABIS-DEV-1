import factory
from factory.django import DjangoModelFactory

from apps.appointments.models import Station
from apps.basedata.tests.factories import PersonFactory
from apps.enrollment.models import Enrollment


class StationFactory(DjangoModelFactory):
    class Meta:
        model = Station
        django_get_or_create = ("code",)

    code = factory.Sequence(lambda n: f"BES-{n:03d}")
    name = factory.Sequence(lambda n: f"Enrollment Station {n:03d}")


class EnrollmentFactory(DjangoModelFactory):
    class Meta:
        model = Enrollment

    person = factory.SubFactory(PersonFactory)
    station = factory.SubFactory(StationFactory)
