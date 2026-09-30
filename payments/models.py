import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from bookings.models import Booking


class PaymentAttempt(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    booking = models.OneToOneField(Booking, related_name="payment", on_delete=models.PROTECT)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="payment_attempts", on_delete=models.CASCADE)
    provider_reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    idempotency_key = models.CharField(max_length=128)
    request_fingerprint = models.CharField(max_length=64)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, default="INR")
    requested_outcome = models.CharField(max_length=16, choices=Status.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    failure_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=("user", "idempotency_key"), name="unique_payment_idempotency_per_user"),
        ]

    def __str__(self):
        return f"Payment {self.id} for booking {self.booking_id}"


class WebhookEvent(models.Model):
    class Action(models.TextChoices):
        PROCESSED = "PROCESSED", "Processed"
        REPLAYED = "REPLAYED", "Replayed"
        DUPLICATE_RESULT = "DUPLICATE_RESULT", "Duplicate result"
        IGNORED_CONFLICT = "IGNORED_CONFLICT", "Ignored conflict"
        IGNORED_BOOKING_STATE = "IGNORED_BOOKING_STATE", "Ignored booking state"

    provider_event_id = models.CharField(max_length=160, unique=True)
    provider_reference = models.UUIDField()
    payment = models.ForeignKey(PaymentAttempt, null=True, blank=True, related_name="webhook_events", on_delete=models.SET_NULL)
    outcome = models.CharField(max_length=16, choices=PaymentAttempt.Status.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, default="INR")
    payload_hash = models.CharField(max_length=64)
    action = models.CharField(max_length=32, choices=Action.choices)
    message = models.CharField(max_length=255, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-received_at",)

    def __str__(self):
        return self.provider_event_id
