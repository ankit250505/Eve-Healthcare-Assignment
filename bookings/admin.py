from django.contrib import admin

from bookings.models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "test_name", "centre_name", "appointment_at", "amount", "status")
    list_filter = ("status", "appointment_at", "created_at")
    search_fields = ("user__email", "test_name", "centre_name")
    readonly_fields = ("amount", "currency", "centre_name", "test_name", "created_at", "updated_at", "cancelled_at")
