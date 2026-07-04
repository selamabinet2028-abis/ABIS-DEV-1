from rest_framework.routers import DefaultRouter

from .views import (InvestigationCategoryViewSet, LookupValueViewSet,
                    OrgUnitViewSet, PersonViewSet)

router = DefaultRouter()
router.register("persons", PersonViewSet, basename="person")
router.register("org-units", OrgUnitViewSet, basename="org-unit")
router.register("lookups", LookupValueViewSet, basename="lookup")
router.register(
    "investigation-categories",
    InvestigationCategoryViewSet,
    basename="investigation-category",
)

urlpatterns = router.urls
