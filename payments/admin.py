from django.contrib import admin

from payments.models import PaymentAttempt, WebhookEvent


@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "booking", "user", "status", "amount", "currency", "provider_reference", "created_at")
    list_filter = ("status", "currency", "created_at")
    search_fields = ("booking__id", "user__email", "provider_reference", "idempotency_key")
    readonly_fields = ("provider_reference", "request_fingerprint", "created_at", "updated_at")


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ("provider_event_id", "provider_reference", "outcome", "action", "received_at")
    list_filter = ("outcome", "action", "received_at")
    search_fields = ("provider_event_id", "provider_reference", "payment__id")
    readonly_fields = ("provider_event_id", "payload_hash", "received_at")
