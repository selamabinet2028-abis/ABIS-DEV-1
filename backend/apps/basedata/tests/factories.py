import factory
from factory.django import DjangoModelFactory

from apps.basedata.models import (InvestigationCategory, LookupValue, OrgUnit,
                                  Person)


class OrgUnitFactory(DjangoModelFactory):
    class Meta:
        model = OrgUnit

    name = factory.Sequence(lambda n: f"Unit {n:03d}")


class PersonFactory(DjangoModelFactory):
    class Meta:
        model = Person

    first_name = factory.Faker("first_name")
    middle_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    gender = Person.Gender.MALE
    nationality = "Ethiopian"
    addresses = factory.LazyFunction(
        lambda: [{"region": "Addis Ababa", "sub_city": "Bole", "woreda": "03"}]
    )


class LookupValueFactory(DjangoModelFactory):
    class Meta:
        model = LookupValue

    category = "purpose"
    code = factory.Sequence(lambda n: f"code-{n:03d}")
    label = factory.Sequence(lambda n: f"Label {n:03d}")


class InvestigationCategoryFactory(DjangoModelFactory):
    class Meta:
        model = InvestigationCategory

    code = factory.Sequence(lambda n: f"IC-{n:03d}")
    name = factory.Sequence(lambda n: f"Category {n:03d}")
