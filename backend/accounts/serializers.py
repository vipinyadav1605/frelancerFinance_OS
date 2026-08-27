from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import BusinessProfile, User
from .validators import validate_gstin_format, validate_pan_format


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["id", "email", "name", "password"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    has_business_profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "name", "has_business_profile"]

    def get_has_business_profile(self, obj):
        return BusinessProfile.objects.filter(user=obj).exists()


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, validators=[validate_password])


class BusinessProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessProfile
        fields = [
            "id", "business_name", "pan", "gstin", "is_gst_registered",
            "address", "state", "invoice_prefix", "lut_reference",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_gstin(self, value):
        return validate_gstin_format(value)

    def validate_pan(self, value):
        return validate_pan_format(value)
