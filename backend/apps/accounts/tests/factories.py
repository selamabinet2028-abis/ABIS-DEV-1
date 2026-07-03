import factory
from factory.django import DjangoModelFactory

from apps.accounts.models import Role, User

DEFAULT_PASSWORD = "Str0ng!Passw0rd42"


class RoleFactory(DjangoModelFactory):
    class Meta:
        model = Role
        django_get_or_create = ("name",)

    name = Role.OPERATOR


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user{n:04d}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@efpc.gov.et")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    badge_number = factory.Sequence(lambda n: f"EFP-{n:05d}")
    is_active = True

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        obj.set_password(extracted or DEFAULT_PASSWORD)
        if create:
            obj.save(update_fields=["password"])
