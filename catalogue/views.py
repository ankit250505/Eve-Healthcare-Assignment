from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsStaffOrReadOnly
from catalogue.models import CentreTest, DiagnosticCentre, DiagnosticTest
from catalogue.serializers import CentreTestSerializer, DiagnosticCentreSerializer, DiagnosticTestSerializer


class SoftDeleteMixin:
    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=("is_active", "updated_at"))


class DiagnosticCentreViewSet(SoftDeleteMixin, viewsets.ModelViewSet):
    permission_classes = (IsStaffOrReadOnly,)
    serializer_class = DiagnosticCentreSerializer

    def get_queryset(self):
        queryset = DiagnosticCentre.objects.all()
        if not (self.request.user and self.request.user.is_authenticated and self.request.user.is_staff):
            queryset = queryset.filter(is_active=True)
        city = self.request.query_params.get("city")
        if city:
            queryset = queryset.filter(city__iexact=city)
        return queryset

    @action(detail=True, methods=["get"], permission_classes=(permissions.AllowAny,), url_path="tests")
    def tests(self, request, pk=None):
        centre = self.get_object()
        offerings = centre.offerings.select_related("centre", "test").filter(
            is_active=True,
            test__is_active=True,
        )
        page = self.paginate_queryset(offerings)
        if page is not None:
            serializer = CentreTestSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(CentreTestSerializer(offerings, many=True).data)


class DiagnosticTestViewSet(SoftDeleteMixin, viewsets.ModelViewSet):
    permission_classes = (IsStaffOrReadOnly,)
    serializer_class = DiagnosticTestSerializer

    def get_queryset(self):
        queryset = DiagnosticTest.objects.all()
        if not (self.request.user and self.request.user.is_authenticated and self.request.user.is_staff):
            queryset = queryset.filter(is_active=True)
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset


class CentreTestViewSet(SoftDeleteMixin, viewsets.ModelViewSet):
    permission_classes = (IsStaffOrReadOnly,)
    serializer_class = CentreTestSerializer

    def get_queryset(self):
        queryset = CentreTest.objects.select_related("centre", "test")
        if not (self.request.user and self.request.user.is_authenticated and self.request.user.is_staff):
            queryset = queryset.filter(is_active=True, centre__is_active=True, test__is_active=True)
        centre_id = self.request.query_params.get("centre_id")
        test_id = self.request.query_params.get("test_id")
        if centre_id:
            queryset = queryset.filter(centre_id=centre_id)
        if test_id:
            queryset = queryset.filter(test_id=test_id)
        return queryset
