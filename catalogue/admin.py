from django.contrib import admin

from catalogue.models import CentreTest, DiagnosticCentre, DiagnosticTest


@admin.register(DiagnosticCentre)
class DiagnosticCentreAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "is_active")
    list_filter = ("city", "is_active")
    search_fields = ("name", "city", "address")


@admin.register(DiagnosticTest)
class DiagnosticTestAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")


@admin.register(CentreTest)
class CentreTestAdmin(admin.ModelAdmin):
    list_display = ("centre", "test", "price", "is_active")
    list_filter = ("is_active", "centre")
    search_fields = ("centre__name", "test__name", "test__code")
