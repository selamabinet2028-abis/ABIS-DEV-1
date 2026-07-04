import factory
from django.core.files.uploadedfile import SimpleUploadedFile
from factory.django import DjangoModelFactory

from apps.investigation.models import Case, LatentPrint
from apps.matching.tests.helpers import png_bytes
from apps.preprocessing.services import sha256_hex


class CaseFactory(DjangoModelFactory):
    class Meta:
        model = Case

    title = factory.Sequence(lambda n: f"Case file {n:04d}")


class LatentFactory(DjangoModelFactory):
    class Meta:
        model = LatentPrint

    case = factory.SubFactory(CaseFactory)
    modality = LatentPrint.Modality.FINGER

    @factory.lazy_attribute
    def image(self):
        payload = png_bytes(self.image_seed)
        return SimpleUploadedFile("latent.png", payload, content_type="image/png")

    @factory.lazy_attribute
    def sha256(self):
        return sha256_hex(png_bytes(self.image_seed))

    class Params:
        image_seed = 9000
