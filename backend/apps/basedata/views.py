from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.audit.services import log_search

from .models import InvestigationCategory, LookupValue, OrgUnit, Person
from .permissions import BaseDataAdminWrite, PersonPermission
from .serializers import (InvestigationCategorySerializer,
                          LookupValueSerializer, OrgUnitSerializer,
                          PersonPhotoSerializer, PersonSerializer)


class PersonViewSet(viewsets.ModelViewSet):
    """Person cards. Soft delete only; every search is audited (golden rule #4)."""

    queryset = Person.objects.filter(is_deleted=False)
    serializer_class = PersonSerializer
    permission_classes = [PersonPermission]
    search_fields = [
        "first_name",
        "middle_name",
        "last_name",
        "person_no",
        "national_id_no",
    ]
    filterset_fields = ["gender", "nationality"]
    ordering_fields = ["person_no", "last_name", "created_at"]

    def list(self, request, *args, **kwargs):
        if request.query_params.get("search"):
            log_search("basedata.Person", dict(request.query_params.items()))
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Soft-delete person (evidentiary retention)", responses={204: None}
    )
    def destroy(self, request, *args, **kwargs):
        person = self.get_object()
        person.is_deleted = True
        person.save(update_fields=["is_deleted"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        summary="Upload person photo (jpg/png, size-limited)",
        request=PersonPhotoSerializer,
        responses=PersonSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser],
        serializer_class=PersonPhotoSerializer,
    )
    def photo(self, request, pk=None):
        person = self.get_object()
        serializer = PersonPhotoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        person.photo = serializer.validated_data["photo"]
        person.save(update_fields=["photo"])
        return Response(PersonSerializer(person, context={"request": request}).data)


class OrgUnitViewSet(viewsets.ModelViewSet):
    queryset = OrgUnit.objects.select_related("parent").all()
    serializer_class = OrgUnitSerializer
    permission_classes = [BaseDataAdminWrite]
    search_fields = ["name"]
    filterset_fields = ["parent"]


class LookupValueViewSet(viewsets.ModelViewSet):
    queryset = LookupValue.objects.all()
    serializer_class = LookupValueSerializer
    permission_classes = [BaseDataAdminWrite]
    filterset_fields = ["category", "is_active"]
    search_fields = ["code", "label"]


class InvestigationCategoryViewSet(viewsets.ModelViewSet):
    queryset = InvestigationCategory.objects.all()
    serializer_class = InvestigationCategorySerializer
    permission_classes = [BaseDataAdminWrite]
    filterset_fields = ["is_active"]
    search_fields = ["code", "name"]
