from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (InitiatePaymentView, PaymentViewSet, PaymentWebhookView,
                    ReconcileView, ReconciliationBatchViewSet)

router = DefaultRouter()
router.register(
    "payments/reconciliations", ReconciliationBatchViewSet, basename="reconciliation"
)
router.register("payments", PaymentViewSet, basename="payment")

urlpatterns = [
    path("payments/initiate/", InitiatePaymentView.as_view(), name="payment-initiate"),
    path(
        "payments/webhook/<str:provider>/",
        PaymentWebhookView.as_view(),
        name="payment-webhook",
    ),
    path("payments/reconcile/", ReconcileView.as_view(), name="payment-reconcile"),
    *router.urls,
]
