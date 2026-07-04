from rest_framework.routers import DefaultRouter

from .views import CaseViewSet, LatentPrintViewSet

router = DefaultRouter()
router.register("cases", CaseViewSet, basename="case")
router.register("latents", LatentPrintViewSet, basename="latent")

urlpatterns = router.urls
