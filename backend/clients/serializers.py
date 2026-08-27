from rest_framework import serializers

from accounts.validators import validate_gstin_format

from .models import Client


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = [
            "id", "name", "email", "billing_address", "country", "state",
            "gstin", "is_international", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "is_international", "created_at", "updated_at"]

    def validate_gstin(self, value):
        return validate_gstin_format(value)

    def validate(self, attrs):
        country = attrs.get("country", getattr(self.instance, "country", "India"))
        state = attrs.get("state", getattr(self.instance, "state", ""))
        if country.strip().lower() == "india" and not state:
            raise serializers.ValidationError(
                {"state": "State is required for domestic (Indian) clients."}
            )
        return attrs
