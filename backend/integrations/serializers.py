import secrets

from rest_framework import serializers

from .models import ApiKey, WebhookDelivery, WebhookSubscription
from .services.api_keys import create_api_key
from .services.url_safety import UnsafeWebhookUrlError, assert_safe_webhook_url


class ApiKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = ApiKey
        fields = ["id", "name", "display_prefix", "is_active", "last_used_at", "created_at"]


class ApiKeyCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)

    def create(self, validated_data):
        api_key, full_key = create_api_key(user=self.context["request"].user, name=validated_data["name"])
        return {"api_key": api_key, "key": full_key}

    def to_representation(self, instance):
        return {
            **ApiKeySerializer(instance["api_key"]).data,
            "key": instance["key"],
        }


class WebhookDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookDelivery
        fields = ["id", "event", "status_code", "success", "error_message", "created_at"]


class WebhookSubscriptionSerializer(serializers.ModelSerializer):
    recent_deliveries = serializers.SerializerMethodField()

    class Meta:
        model = WebhookSubscription
        fields = ["id", "url", "event", "secret", "is_active", "created_at", "recent_deliveries"]
        read_only_fields = ["secret"]

    def get_recent_deliveries(self, obj):
        return WebhookDeliverySerializer(obj.deliveries.all()[:5], many=True).data

    def validate_url(self, value):
        try:
            assert_safe_webhook_url(value)
        except UnsafeWebhookUrlError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return value

    def create(self, validated_data):
        return WebhookSubscription.objects.create(
            user=self.context["request"].user, secret=secrets.token_hex(32), **validated_data
        )
