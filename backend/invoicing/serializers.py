from decimal import Decimal

from rest_framework import serializers

from clients.models import Client

from .models import Invoice, InvoiceItem, Payment, RecurringInvoiceItem, RecurringInvoiceProfile


class InvoiceItemInputSerializer(serializers.Serializer):
    description = serializers.CharField(max_length=255)
    hsn_sac_code = serializers.CharField(max_length=10, required=False, allow_blank=True)
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.01"))
    unit_price = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0"))
    tax_rate_percent = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, default=0)


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = ["id", "description", "hsn_sac_code", "quantity", "unit_price", "tax_rate_percent", "amount"]


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "amount", "payment_date", "method", "razorpay_payment_id", "status", "created_at"]


class InvoiceCreateSerializer(serializers.Serializer):
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.none())
    issue_date = serializers.DateField()
    due_date = serializers.DateField()
    currency = serializers.ChoiceField(choices=["INR", "USD", "EUR", "GBP"], default="INR")
    exchange_rate_to_inr = serializers.DecimalField(max_digits=12, decimal_places=4, default=1)
    items = InvoiceItemInputSerializer(many=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request is not None:
            self.fields["client"].queryset = Client.objects.filter(user=request.user)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("An invoice needs at least one line item.")
        return value

    def validate(self, attrs):
        if attrs["due_date"] < attrs["issue_date"]:
            raise serializers.ValidationError(
                {"due_date": "Due date cannot be before the issue date."}
            )
        return attrs


class InvoiceListSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client_name_snapshot")

    class Meta:
        model = Invoice
        fields = [
            "id", "invoice_number", "client_name", "issue_date", "due_date",
            "currency", "total_amount", "status",
        ]


class InvoiceDetailSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            "id", "invoice_number", "client", "client_name_snapshot", "client_email_snapshot",
            "client_address_snapshot", "client_country_snapshot", "client_gstin_snapshot",
            "issue_date", "due_date", "currency", "exchange_rate_to_inr", "tax_type",
            "lut_reference", "subtotal", "cgst_amount", "sgst_amount", "igst_amount",
            "total_amount", "status", "payment_link_url", "pdf_url", "sent_at", "paid_at",
            "created_at", "items", "payments", "public_view_token",
        ]

    def get_pdf_url(self, obj):
        request = self.context.get("request")
        if obj.pdf_file and request:
            return request.build_absolute_uri(obj.pdf_file.url)
        return None


class PublicInvoiceSerializer(serializers.ModelSerializer):
    """
    For the no-login client-facing view (invoicing/views.py::PublicInvoiceView).
    Deliberately excludes internal ids and the owner's account-level fields -
    only what a client legitimately needs to review and pay their own invoice.
    """

    items = InvoiceItemSerializer(many=True, read_only=True)
    business_name = serializers.CharField(source="user.business_profile.business_name", read_only=True)
    business_gstin = serializers.CharField(source="user.business_profile.gstin", read_only=True)
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            "invoice_number", "business_name", "business_gstin", "client_name_snapshot",
            "client_address_snapshot", "client_country_snapshot", "client_gstin_snapshot",
            "issue_date", "due_date", "currency", "tax_type", "lut_reference", "subtotal",
            "cgst_amount", "sgst_amount", "igst_amount", "total_amount", "status",
            "payment_link_url", "pdf_url", "items",
        ]

    def get_pdf_url(self, obj):
        request = self.context.get("request")
        if obj.pdf_file and request:
            return request.build_absolute_uri(obj.pdf_file.url)
        return None


class MarkPaidSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    payment_date = serializers.DateTimeField()


class RecurringInvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecurringInvoiceItem
        fields = ["description", "hsn_sac_code", "quantity", "unit_price", "tax_rate_percent"]


class RecurringInvoiceProfileSerializer(serializers.ModelSerializer):
    items = RecurringInvoiceItemSerializer(many=True)
    client_name = serializers.CharField(source="client.name", read_only=True)
    last_generated_invoice_number = serializers.CharField(
        source="last_generated_invoice.invoice_number", read_only=True, default=None
    )

    class Meta:
        model = RecurringInvoiceProfile
        fields = [
            "id", "client", "client_name", "frequency", "currency", "exchange_rate_to_inr",
            "due_in_days", "next_run_date", "is_active", "auto_send",
            "last_generated_invoice_number", "items", "created_at",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request is not None:
            self.fields["client"].queryset = Client.objects.filter(user=request.user)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("A recurring profile needs at least one line item.")
        return value

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        profile = RecurringInvoiceProfile.objects.create(
            user=self.context["request"].user, **validated_data
        )
        RecurringInvoiceItem.objects.bulk_create(
            [RecurringInvoiceItem(profile=profile, **item) for item in items_data]
        )
        return profile

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        if items_data is not None:
            instance.items.all().delete()
            RecurringInvoiceItem.objects.bulk_create(
                [RecurringInvoiceItem(profile=instance, **item) for item in items_data]
            )
        return instance


class ExchangeRateQuerySerializer(serializers.Serializer):
    currency = serializers.ChoiceField(choices=["USD", "EUR", "GBP"])
