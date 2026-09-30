import hashlib
import json
from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import NotFound, ValidationError

from bookings.models import Booking
from payments.exceptions import Conflict
from payments.models import PaymentAttempt, WebhookEvent


@dataclass(frozen=True)
class PaymentServiceResult:
    payment: PaymentAttempt
    replayed: bool = False


@dataclass(frozen=True)
class WebhookServiceResult:
    event: WebhookEvent
    replayed: bool = False


def _canonical_hash(data):
    normalized = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def create_mock_payment(*, user, booking_id, simulated_outcome, idempotency_key):
    if not idempotency_key:
        raise ValidationError({"Idempotency-Key": "This header is required."})

    normalized_request = {
        "booking_id": int(booking_id),
        "simulated_outcome": simulated_outcome,
    }
    request_fingerprint = _canonical_hash(normalized_request)

    existing = PaymentAttempt.objects.select_related("booking").filter(
        user=user,
        idempotency_key=idempotency_key,
    ).first()
    if existing:
        if existing.request_fingerprint != request_fingerprint:
            raise Conflict("This Idempotency-Key was already used with a different payment request.")
        return PaymentServiceResult(payment=existing, replayed=True)

    try:
        with transaction.atomic():
            booking = Booking.objects.select_for_update().filter(pk=booking_id, user=user).first()
            if booking is None:
                raise NotFound("Booking not found.")
            if booking.status != Booking.Status.PENDING:
                raise Conflict("Payments can only be created for pending bookings.")
            if PaymentAttempt.objects.filter(booking=booking).exists():
                raise Conflict("This booking already has a payment attempt.")

            payment = PaymentAttempt.objects.create(
                booking=booking,
                user=user,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
                amount=booking.amount,
                currency=booking.currency,
                requested_outcome=simulated_outcome,
            )
    except IntegrityError as exc:
        raise Conflict("A payment attempt already exists for this booking or idempotency key.") from exc

    payload = {
        "event_id": f"mock-payment-{payment.provider_reference}",
        "provider_reference": payment.provider_reference,
        "outcome": simulated_outcome,
        "amount": payment.amount,
        "currency": payment.currency,
    }
    process_payment_webhook(payload)
    payment.refresh_from_db()
    return PaymentServiceResult(payment=payment)


def process_payment_webhook(payload):
    payload_hash = _canonical_hash(payload)
    provider_event_id = payload["event_id"]

    existing = WebhookEvent.objects.select_related("payment").filter(provider_event_id=provider_event_id).first()
    if existing:
        if existing.payload_hash != payload_hash:
            raise Conflict("This provider event id was already used with a different payload.")
        return WebhookServiceResult(event=existing, replayed=True)

    with transaction.atomic():
        payment = PaymentAttempt.objects.select_for_update().select_related("booking").filter(
            provider_reference=payload["provider_reference"]
        ).first()
        if payment is None:
            raise NotFound("Payment reference not found.")

        booking = Booking.objects.select_for_update().get(pk=payment.booking_id)
        outcome = payload["outcome"]
        action = WebhookEvent.Action.PROCESSED
        message = ""

        if payload["currency"] != payment.currency or payload["amount"] != payment.amount:
            raise ValidationError("Webhook amount or currency does not match the payment attempt.")

        if payment.status != PaymentAttempt.Status.PENDING:
            if payment.status == outcome:
                action = WebhookEvent.Action.DUPLICATE_RESULT
                message = "Payment already has this terminal result."
            else:
                action = WebhookEvent.Action.IGNORED_CONFLICT
                message = "Payment already has a different terminal result."
        elif booking.status == Booking.Status.PENDING:
            payment.status = outcome
            if outcome == PaymentAttempt.Status.SUCCESS:
                booking.status = Booking.Status.CONFIRMED
            else:
                booking.status = Booking.Status.FAILED
                payment.failure_reason = "Simulated payment failure."
            payment.save(update_fields=("status", "failure_reason", "updated_at"))
            booking.save(update_fields=("status", "updated_at"))
        else:
            payment.status = outcome
            if outcome == PaymentAttempt.Status.FAILED:
                payment.failure_reason = "Simulated payment failure after booking state changed."
            payment.save(update_fields=("status", "failure_reason", "updated_at"))
            action = WebhookEvent.Action.IGNORED_BOOKING_STATE
            message = f"Booking is {booking.status}; booking state was not changed."

        try:
            with transaction.atomic():
                event = WebhookEvent.objects.create(
                    provider_event_id=provider_event_id,
                    provider_reference=payment.provider_reference,
                    payment=payment,
                    outcome=outcome,
                    amount=payload["amount"],
                    currency=payload["currency"],
                    payload_hash=payload_hash,
                    action=action,
                    message=message,
                )
        except IntegrityError as exc:
            existing = WebhookEvent.objects.select_related("payment").get(provider_event_id=provider_event_id)
            if existing.payload_hash != payload_hash:
                raise Conflict("This provider event id was already used with a different payload.") from exc
            return WebhookServiceResult(event=existing, replayed=True)

    return WebhookServiceResult(event=event)


def get_user_payment_or_404(*, user, payment_id):
    return get_object_or_404(PaymentAttempt.objects.select_related("booking"), pk=payment_id, user=user)
