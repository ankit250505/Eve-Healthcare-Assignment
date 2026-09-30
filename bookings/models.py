from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from catalogue.models import CentreTest


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="bookings", on_delete=models.CASCADE)
    offering = models.ForeignKey(CentreTest, related_name="bookings", on_delete=models.PROTECT)
    centre_name = models.CharField(max_length=160)
    centre_city = models.CharField(max_length=80)
    test_name = models.CharField(max_length=160)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, default="INR")
    appointment_at = models.DateTimeField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("user", "status")),
            models.Index(fields=("appointment_at",)),
        ]

    def __str__(self):
        return f"Booking {self.id} - {self.user_id} - {self.status}"
