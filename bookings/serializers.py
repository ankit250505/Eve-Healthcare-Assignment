from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import serializers

from bookings.models import Booking
from catalogue.models import CentreTest
from catalogue.serializers import CentreTestSerializer


class OffsetDateTimeField(serializers.DateTimeField):
    def to_internal_value(self, value):
        if isinstance(value, str):
            parsed = parse_datetime(value)
            if parsed is None:
                self.fail("invalid", format="ISO 8601")
            if timezone.is_naive(parsed):
                raise serializers.ValidationError("Use an ISO 8601 datetime with a timezone offset.")
        return super().to_internal_value(value)


class BookingSerializer(serializers.ModelSerializer):
    offering = CentreTestSerializer(read_only=True)

    class Meta:
        model = Booking
        fields = (
            "id",
            "offering",
            "centre_name",
            "centre_city",
            "test_name",
            "amount",
            "currency",
            "appointment_at",
            "status",
            "cancelled_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class BookingCreateSerializer(serializers.ModelSerializer):
    offering_id = serializers.PrimaryKeyRelatedField(
        queryset=CentreTest.objects.select_related("centre", "test").filter(
            is_active=True,
            centre__is_active=True,
            test__is_active=True,
        ),
        source="offering",
        write_only=True,
    )
    appointment_at = OffsetDateTimeField()

    class Meta:
        model = Booking
        fields = ("id", "offering_id", "appointment_at")
        read_only_fields = ("id",)

    def validate_appointment_at(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Appointment time must be in the future.")
        return value

    def create(self, validated_data):
        offering = validated_data["offering"]
        request = self.context["request"]
        return Booking.objects.create(
            user=request.user,
            offering=offering,
            centre_name=offering.centre.name,
            centre_city=offering.centre.city,
            test_name=offering.test.name,
            amount=offering.price,
            appointment_at=validated_data["appointment_at"],
        )
