from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from .models import ReportShareLink, TaxEstimate


class TaxEstimateSerializer(serializers.ModelSerializer):
    income_tax_detail = serializers.SerializerMethodField()

    class Meta:
        model = TaxEstimate
        fields = [
            "period_start", "period_end", "total_income", "total_expense", "net_profit",
            "gst_output_tax", "gst_input_tax_credit", "estimated_gst_liability",
            "financial_year_start", "financial_year_end", "financial_year_gross_receipts",
            "estimated_income_tax", "income_tax_detail", "computed_at",
        ]

    def get_income_tax_detail(self, obj):
        detail = getattr(obj, "_income_tax_detail", None)
        return detail


class PeriodQuerySerializer(serializers.Serializer):
    period_start = serializers.DateField()
    period_end = serializers.DateField()

    def validate(self, attrs):
        if attrs["period_end"] < attrs["period_start"]:
            raise serializers.ValidationError({"period_end": "period_end cannot be before period_start."})
        return attrs


class ReportShareLinkCreateSerializer(serializers.Serializer):
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    label = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    expires_in_days = serializers.IntegerField(min_value=1, max_value=90, default=14)

    def validate(self, attrs):
        if attrs["period_end"] < attrs["period_start"]:
            raise serializers.ValidationError({"period_end": "period_end cannot be before period_start."})
        return attrs

    def create(self, validated_data):
        expires_in_days = validated_data.pop("expires_in_days")
        return ReportShareLink.objects.create(
            user=self.context["request"].user,
            expires_at=timezone.now() + timedelta(days=expires_in_days),
            **validated_data,
        )


class ReportShareLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportShareLink
        fields = ["id", "token", "period_start", "period_end", "label", "expires_at", "created_at"]
