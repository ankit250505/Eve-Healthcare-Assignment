from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from bookings.models import Booking
from catalogue.models import CentreTest, DiagnosticCentre, DiagnosticTest

User = get_user_model()


def create_offering(price=Decimal("499.00"), active=True):
    centre = DiagnosticCentre.objects.create(
        name="EVE Diagnostics Green Park",
        city="Delhi",
        address="A-18 Green Park Main",
        is_active=active,
    )
    test = DiagnosticTest.objects.create(
        name="Complete Blood Count",
        code=f"cbc-{DiagnosticTest.objects.count()}",
        description="Blood cell count screening.",
        is_active=active,
    )
    return CentreTest.objects.create(centre=centre, test=test, price=price, is_active=active)


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class BookingApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="patient@example.com", password="StrongPass123!")
        self.other_user = User.objects.create_user(email="other@example.com", password="StrongPass123!")
        self.offering = create_offering()
        self.client.force_authenticate(self.user)

    def test_create_booking_snapshots_catalogue_price(self):
        appointment = (timezone.now() + timedelta(days=2)).isoformat()

        response = self.client.post(
            "/api/bookings/",
            {"offering_id": self.offering.id, "appointment_at": appointment},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        booking = Booking.objects.get(id=response.data["id"])
        self.assertEqual(booking.status, Booking.Status.PENDING)
        self.assertEqual(booking.amount, Decimal("499.00"))

        self.offering.price = Decimal("999.00")
        self.offering.save(update_fields=("price", "updated_at"))
        booking.refresh_from_db()

        self.assertEqual(booking.amount, Decimal("499.00"))

    def test_booking_requires_future_timezone_aware_appointment(self):
        naive_response = self.client.post(
            "/api/bookings/",
            {"offering_id": self.offering.id, "appointment_at": "2026-10-05T10:30:00"},
            format="json",
        )
        past_response = self.client.post(
            "/api/bookings/",
            {"offering_id": self.offering.id, "appointment_at": (timezone.now() - timedelta(hours=1)).isoformat()},
            format="json",
        )

        self.assertEqual(naive_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(past_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_cannot_access_another_users_booking(self):
        booking = Booking.objects.create(
            user=self.other_user,
            offering=self.offering,
            centre_name=self.offering.centre.name,
            centre_city=self.offering.centre.city,
            test_name=self.offering.test.name,
            amount=self.offering.price,
            appointment_at=timezone.now() + timedelta(days=2),
        )

        response = self.client.get(f"/api/bookings/{booking.id}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cancel_pending_booking_is_idempotent(self):
        booking = Booking.objects.create(
            user=self.user,
            offering=self.offering,
            centre_name=self.offering.centre.name,
            centre_city=self.offering.centre.city,
            test_name=self.offering.test.name,
            amount=self.offering.price,
            appointment_at=timezone.now() + timedelta(days=2),
        )

        first_response = self.client.post(f"/api/bookings/{booking.id}/cancel/")
        second_response = self.client.post(f"/api/bookings/{booking.id}/cancel/")

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELLED)
        self.assertIsNotNone(booking.cancelled_at)

    def test_confirmed_booking_cannot_be_cancelled(self):
        booking = Booking.objects.create(
            user=self.user,
            offering=self.offering,
            centre_name=self.offering.centre.name,
            centre_city=self.offering.centre.city,
            test_name=self.offering.test.name,
            amount=self.offering.price,
            appointment_at=timezone.now() + timedelta(days=2),
            status=Booking.Status.CONFIRMED,
        )

        response = self.client.post(f"/api/bookings/{booking.id}/cancel/")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
