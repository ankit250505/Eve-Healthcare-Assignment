from rest_framework import serializers

from payments.models import PaymentAttempt, WebhookEvent


class PaymentCreateSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField(min_value=1)
    simulated_outcome = serializers.ChoiceField(choices=(PaymentAttempt.Status.SUCCESS, PaymentAttempt.Status.FAILED))


class PaymentAttemptSerializer(serializers.ModelSerializer):
    booking_id = serializers.IntegerField(source="booking.id", read_only=True)

    class Meta:
        model = PaymentAttempt
        fields = (
            "id",
            "booking_id",
            "provider_reference",
            "amount",
            "currency",
            "requested_outcome",
            "status",
            "failure_reason",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class WebhookPayloadSerializer(serializers.Serializer):
    event_id = serializers.CharField(max_length=160)
    provider_reference = serializers.UUIDField()
    outcome = serializers.ChoiceField(choices=(PaymentAttempt.Status.SUCCESS, PaymentAttempt.Status.FAILED))
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(max_length=3, default="INR")


class WebhookEventSerializer(serializers.ModelSerializer):
    payment_id = serializers.IntegerField(source="payment.id", read_only=True)

    class Meta:
        model = WebhookEvent
        fields = (
            "provider_event_id",
            "provider_reference",
            "payment_id",
            "outcome",
            "amount",
            "currency",
            "action",
            "message",
            "received_at",
        )
        read_only_fields = fields
