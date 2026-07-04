from rest_framework import serializers

from .models import Payment, ReconciliationBatch


class PaymentSerializer(serializers.ModelSerializer):
    tracking_no = serializers.CharField(
        source="application.tracking_no", read_only=True
    )
    initiated_by_username = serializers.CharField(
        source="initiated_by.username", read_only=True, default=None
    )

    class Meta:
        model = Payment
        fields = [
            "id",
            "application",
            "tracking_no",
            "amount",
            "currency",
            "method",
            "status",
            "gateway_ref",
            "receipt_no",
            "paid_at",
            "initiated_by_username",
            "created_at",
        ]
        read_only_fields = fields


class InitiateSerializer(serializers.Serializer):
    application_id = serializers.UUIDField()
    method = serializers.ChoiceField(choices=Payment.Method.choices)


class InitiateResponseSerializer(serializers.Serializer):
    payment_id = serializers.UUIDField()
    checkout_ref = serializers.CharField(allow_blank=True)
    status = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    receipt_no = serializers.CharField(allow_null=True)


class ReconcileRequestSerializer(serializers.Serializer):
    date_from = serializers.DateField(required=False, allow_null=True)
    date_to = serializers.DateField(required=False, allow_null=True)


class ReconciliationBatchSerializer(serializers.ModelSerializer):
    run_by_username = serializers.CharField(
        source="run_by.username", read_only=True, default=None
    )

    class Meta:
        model = ReconciliationBatch
        fields = [
            "id",
            "date_from",
            "date_to",
            "totals",
            "run_by_username",
            "created_at",
        ]
        read_only_fields = fields
