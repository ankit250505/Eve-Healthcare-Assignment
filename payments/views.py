from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from payments.serializers import PaymentAttemptSerializer, PaymentCreateSerializer, WebhookEventSerializer, WebhookPayloadSerializer
from payments.services import create_mock_payment, process_payment_webhook


class PaymentCreateView(generics.GenericAPIView):
    serializer_class = PaymentCreateSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = create_mock_payment(
            user=request.user,
            booking_id=serializer.validated_data["booking_id"],
            simulated_outcome=serializer.validated_data["simulated_outcome"],
            idempotency_key=request.headers.get("Idempotency-Key", ""),
        )
        response_status = status.HTTP_200_OK if result.replayed else status.HTTP_201_CREATED
        return Response(PaymentAttemptSerializer(result.payment).data, status=response_status)


class PaymentDetailView(generics.RetrieveAPIView):
    serializer_class = PaymentAttemptSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return self.request.user.payment_attempts.select_related("booking")


class PaymentWebhookView(generics.GenericAPIView):
    serializer_class = WebhookPayloadSerializer
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    def post(self, request):
        if not settings.PAYMENT_WEBHOOK_SECRET:
            return Response({"detail": "Webhook secret is not configured."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        if request.headers.get("X-Webhook-Secret") != settings.PAYMENT_WEBHOOK_SECRET:
            return Response({"detail": "Invalid webhook secret."}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = process_payment_webhook(serializer.validated_data)
        return Response(WebhookEventSerializer(result.event).data, status=status.HTTP_200_OK)
