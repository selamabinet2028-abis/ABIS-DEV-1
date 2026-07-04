from rest_framework.routers import DefaultRouter

from .views import BiometricRecordViewSet, EnrollmentViewSet

router = DefaultRouter()
router.register("enrollments", EnrollmentViewSet, basename="enrollment")
router.register(
    "biometric-records", BiometricRecordViewSet, basename="biometric-record"
)

urlpatterns = router.urls
