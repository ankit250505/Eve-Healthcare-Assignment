from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from bookings.models import Booking
from catalogue.models import CentreTest, DiagnosticCentre, DiagnosticTest
from payments.models import PaymentAttempt, WebhookEvent

User = get_user_model()


def create_offering(price=Decimal("499.00")):
    centre = DiagnosticCentre.objects.create(
        name=f"EVE Centre {DiagnosticCentre.objects.count()}",
        city="Delhi",
        address=f"{DiagnosticCentre.objects.count()} Main Road",
    )
    test = DiagnosticTest.objects.create(
        name=f"Blood Test {DiagnosticTest.objects.count()}",
        code=f"blood-{DiagnosticTest.objects.count()}",
    )
    return CentreTest.objects.create(centre=centre, test=test, price=price)


def create_booking(user, offering, status_value=Booking.Status.PENDING):
    return Booking.objects.create(
        user=user,
        offering=offering,
        centre_name=offering.centre.name,
        centre_city=offering.centre.city,
        test_name=offering.test.name,
        amount=offering.price,
        appointment_at=timezone.now() + timedelta(days=2),
        status=status_value,
    )


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"], PAYMENT_WEBHOOK_SECRET="test-webhook-secret")
class PaymentApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="patient@example.com", password="StrongPass123!")
        self.other_user = User.objects.create_user(email="other@example.com", password="StrongPass123!")
        self.offering = create_offering()
        self.client.force_authenticate(self.user)

    def test_mock_success_payment_confirms_booking_and_replays_idempotently(self):
        booking = create_booking(self.user, self.offering)
        body = {"booking_id": booking.id, "simulated_outcome": PaymentAttempt.Status.SUCCESS}

        first_response = self.client.post(
            "/api/payments/",
            body,
            format="json",
            HTTP_IDEMPOTENCY_KEY="success-key",
        )
        replay_response = self.client.post(
            "/api/payments/",
            body,
            format="json",
            HTTP_IDEMPOTENCY_KEY="success-key",
        )

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(replay_response.status_code, status.HTTP_200_OK)
        self.assertEqual(first_response.data["id"], replay_response.data["id"])
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)
        self.assertEqual(first_response.data["status"], PaymentAttempt.Status.SUCCESS)

    def test_mock_failed_payment_marks_booking_failed(self):
        booking = create_booking(self.user, self.offering)

        response = self.client.post(
            "/api/payments/",
            {"booking_id": booking.id, "simulated_outcome": PaymentAttempt.Status.FAILED},
            format="json",
            HTTP_IDEMPOTENCY_KEY="failed-key",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.FAILED)
        self.assertEqual(response.data["status"], PaymentAttempt.Status.FAILED)

    def test_changed_body_with_same_idempotency_key_returns_conflict(self):
        first_booking = create_booking(self.user, self.offering)
        second_booking = create_booking(self.user, self.offering)

        first_response = self.client.post(
            "/api/payments/",
            {"booking_id": first_booking.id, "simulated_outcome": PaymentAttempt.Status.SUCCESS},
            format="json",
            HTTP_IDEMPOTENCY_KEY="same-key",
        )
        conflict_response = self.client.post(
            "/api/payments/",
            {"booking_id": second_booking.id, "simulated_outcome": PaymentAttempt.Status.SUCCESS},
            format="json",
            HTTP_IDEMPOTENCY_KEY="same-key",
        )

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(conflict_response.status_code, status.HTTP_409_CONFLICT)

    def test_payment_requires_idempotency_key_and_own_pending_booking(self):
        other_booking = create_booking(self.other_user, self.offering)
        own_confirmed_booking = create_booking(self.user, self.offering, Booking.Status.CONFIRMED)

        missing_key_response = self.client.post(
            "/api/payments/",
            {"booking_id": own_confirmed_booking.id, "simulated_outcome": PaymentAttempt.Status.SUCCESS},
            format="json",
        )
        other_booking_response = self.client.post(
            "/api/payments/",
            {"booking_id": other_booking.id, "simulated_outcome": PaymentAttempt.Status.SUCCESS},
            format="json",
            HTTP_IDEMPOTENCY_KEY="other-booking",
        )
        confirmed_response = self.client.post(
            "/api/payments/",
            {"booking_id": own_confirmed_booking.id, "simulated_outcome": PaymentAttempt.Status.SUCCESS},
            format="json",
            HTTP_IDEMPOTENCY_KEY="confirmed-booking",
        )

        self.assertEqual(missing_key_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(other_booking_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(confirmed_response.status_code, status.HTTP_409_CONFLICT)

    def test_webhook_replay_and_changed_payload_conflict(self):
        booking = create_booking(self.user, self.offering)
        payment = PaymentAttempt.objects.create(
            booking=booking,
            user=self.user,
            idempotency_key="manual-key",
            request_fingerprint="fingerprint",
            amount=booking.amount,
            currency=booking.currency,
            requested_outcome=PaymentAttempt.Status.SUCCESS,
        )
        payload = {
            "event_id": "evt-success-1",
            "provider_reference": str(payment.provider_reference),
            "outcome": PaymentAttempt.Status.SUCCESS,
            "amount": str(payment.amount),
            "currency": payment.currency,
        }

        first_response = self.client.post(
            "/api/payments/webhook/",
            payload,
            format="json",
            HTTP_X_WEBHOOK_SECRET="test-webhook-secret",
        )
        replay_response = self.client.post(
            "/api/payments/webhook/",
            payload,
            format="json",
            HTTP_X_WEBHOOK_SECRET="test-webhook-secret",
        )
        changed_payload = {**payload, "outcome": PaymentAttempt.Status.FAILED}
        conflict_response = self.client.post(
            "/api/payments/webhook/",
            changed_payload,
            format="json",
            HTTP_X_WEBHOOK_SECRET="test-webhook-secret",
        )

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(replay_response.status_code, status.HTTP_200_OK)
        self.assertEqual(conflict_response.status_code, status.HTTP_409_CONFLICT)
        booking.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)
        self.assertEqual(payment.status, PaymentAttempt.Status.SUCCESS)

    def test_webhook_conflicting_terminal_result_is_recorded_without_corruption(self):
        booking = create_booking(self.user, self.offering)
        payment = PaymentAttempt.objects.create(
            booking=booking,
            user=self.user,
            idempotency_key="manual-conflict-key",
            request_fingerprint="fingerprint",
            amount=booking.amount,
            currency=booking.currency,
            requested_outcome=PaymentAttempt.Status.SUCCESS,
        )
        success_payload = {
            "event_id": "evt-terminal-success",
            "provider_reference": str(payment.provider_reference),
            "outcome": PaymentAttempt.Status.SUCCESS,
            "amount": str(payment.amount),
            "currency": payment.currency,
        }
        failure_payload = {
            **success_payload,
            "event_id": "evt-terminal-failure",
            "outcome": PaymentAttempt.Status.FAILED,
        }

        success_response = self.client.post(
            "/api/payments/webhook/",
            success_payload,
            format="json",
            HTTP_X_WEBHOOK_SECRET="test-webhook-secret",
        )
        failure_response = self.client.post(
            "/api/payments/webhook/",
            failure_payload,
            format="json",
            HTTP_X_WEBHOOK_SECRET="test-webhook-secret",
        )

        self.assertEqual(success_response.status_code, status.HTTP_200_OK)
        self.assertEqual(failure_response.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        payment.refresh_from_db()
        conflict_event = WebhookEvent.objects.get(provider_event_id="evt-terminal-failure")
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)
        self.assertEqual(payment.status, PaymentAttempt.Status.SUCCESS)
        self.assertEqual(conflict_event.action, WebhookEvent.Action.IGNORED_CONFLICT)

    def test_webhook_rejects_invalid_secret_and_unknown_reference(self):
        unknown_payload = {
            "event_id": "evt-unknown",
            "provider_reference": str(uuid4()),
            "outcome": PaymentAttempt.Status.SUCCESS,
            "amount": "499.00",
            "currency": "INR",
        }

        forbidden_response = self.client.post(
            "/api/payments/webhook/",
            unknown_payload,
            format="json",
            HTTP_X_WEBHOOK_SECRET="wrong-secret",
        )
        not_found_response = self.client.post(
            "/api/payments/webhook/",
            unknown_payload,
            format="json",
            HTTP_X_WEBHOOK_SECRET="test-webhook-secret",
        )

        self.assertEqual(forbidden_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(not_found_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_webhook_amount_mismatch_is_rejected_without_state_change(self):
        booking = create_booking(self.user, self.offering)
        payment = PaymentAttempt.objects.create(
            booking=booking,
            user=self.user,
            idempotency_key="manual-amount-key",
            request_fingerprint="fingerprint",
            amount=booking.amount,
            currency=booking.currency,
            requested_outcome=PaymentAttempt.Status.SUCCESS,
        )

        response = self.client.post(
            "/api/payments/webhook/",
            {
                "event_id": "evt-wrong-amount",
                "provider_reference": str(payment.provider_reference),
                "outcome": PaymentAttempt.Status.SUCCESS,
                "amount": "1.00",
                "currency": payment.currency,
            },
            format="json",
            HTTP_X_WEBHOOK_SECRET="test-webhook-secret",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        booking.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.PENDING)
        self.assertEqual(payment.status, PaymentAttempt.Status.PENDING)
        self.assertFalse(WebhookEvent.objects.filter(provider_event_id="evt-wrong-amount").exists())
