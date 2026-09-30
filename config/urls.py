from django.contrib import admin
from django.views.generic import TemplateView
from django.urls import include, path

from config.views import health

urlpatterns = [
    path("", TemplateView.as_view(template_name="frontend/index.html"), name="frontend-home"),
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("catalogue.urls")),
    path("api/bookings/", include("bookings.urls")),
    path("api/payments/", include("payments.urls")),
]
