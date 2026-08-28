from rest_framework import serializers


class UsageSummarySerializer(serializers.Serializer):
    is_pro = serializers.BooleanField()
    invoices_this_month = serializers.IntegerField()
    free_tier_monthly_invoice_limit = serializers.IntegerField()
