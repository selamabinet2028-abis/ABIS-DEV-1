from django.urls import path

from .views import (InstitutionalVerifyView, PublicQrVerifyView,
                    PublicVerifyView)

urlpatterns = [
    # qr/ must precede the catch-all <verification_no> pattern
    path("public/verify/qr/", PublicQrVerifyView.as_view(), name="public-verify-qr"),
    path(
        "public/verify/<str:verification_no>/",
        PublicVerifyView.as_view(),
        name="public-verify",
    ),
    path("verify/api/", InstitutionalVerifyView.as_view(), name="institutional-verify"),
]
