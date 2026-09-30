from django.db import transaction
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from bookings.exceptions import Conflict
from bookings.models import Booking
from bookings.serializers import BookingCreateSerializer, BookingSerializer


class BookingViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = BookingSerializer

    def get_queryset(self):
        queryset = Booking.objects.select_related("offering", "offering__centre", "offering__test").filter(
            user=self.request.user
        )
        status = self.request.query_params.get("status")
        if status:
            queryset = queryset.filter(status=status.upper())
        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return BookingCreateSerializer
        return BookingSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        return Response(BookingSerializer(booking, context=self.get_serializer_context()).data, status=201)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        with transaction.atomic():
            booking = Booking.objects.select_for_update().filter(pk=pk, user=request.user).first()
            if booking is None:
                raise NotFound()
            if booking.status == Booking.Status.CONFIRMED:
                raise Conflict("Confirmed bookings cannot be cancelled in this version.")
            if booking.status != Booking.Status.CANCELLED:
                booking.status = Booking.Status.CANCELLED
                booking.cancelled_at = timezone.now()
                booking.save(update_fields=("status", "cancelled_at", "updated_at"))

        return Response(BookingSerializer(booking, context=self.get_serializer_context()).data)
