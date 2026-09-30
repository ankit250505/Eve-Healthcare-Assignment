from django.urls import include, path
from rest_framework.routers import DefaultRouter

from catalogue.views import CentreTestViewSet, DiagnosticCentreViewSet, DiagnosticTestViewSet

router = DefaultRouter()
router.register("centres", DiagnosticCentreViewSet, basename="centre")
router.register("tests", DiagnosticTestViewSet, basename="test")
router.register("offerings", CentreTestViewSet, basename="offering")

urlpatterns = [
    path("", include(router.urls)),
]
