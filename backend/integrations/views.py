from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.response import Response

from .models import ApiKey, WebhookSubscription
from .serializers import ApiKeyCreateSerializer, ApiKeySerializer, WebhookSubscriptionSerializer


class ApiKeyViewSet(viewsets.ModelViewSet):
    """Phase 5: personal API keys. The raw key is only ever returned on create."""

    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        return ApiKey.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return ApiKeyCreateSerializer
        return ApiKeySerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(serializer.to_representation(result), status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        api_key = self.get_object()
        api_key.revoked_at = timezone.now()
        api_key.save(update_fields=["revoked_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class WebhookSubscriptionViewSet(viewsets.ModelViewSet):
    """Phase 5: outgoing webhook subscriptions for third-party integrations."""

    serializer_class = WebhookSubscriptionSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return WebhookSubscription.objects.filter(user=self.request.user).prefetch_related("deliveries")
