from rest_framework import serializers

from .models import BankStatementImport, Expense, ExpenseCategory

MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_RECEIPT_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}


def _validate_upload_size(uploaded_file):
    if uploaded_file.size > MAX_UPLOAD_SIZE_BYTES:
        raise serializers.ValidationError(
            f"File is too large ({uploaded_file.size // 1024} KB) - the limit is 5 MB."
        )


class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ["id", "name", "is_default"]
        read_only_fields = ["id", "is_default"]


class ExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    receipt_url = serializers.SerializerMethodField()

    class Meta:
        model = Expense
        fields = [
            "id", "category", "category_name", "vendor_name", "amount", "gst_paid", "expense_date",
            "source", "receipt_file", "receipt_url", "notes", "created_at",
        ]
        read_only_fields = ["id", "source", "created_at"]
        extra_kwargs = {"receipt_file": {"write_only": True, "required": False}}

    def get_receipt_url(self, obj):
        request = self.context.get("request")
        if obj.receipt_file and request:
            return request.build_absolute_uri(obj.receipt_file.url)
        return None

    def validate_receipt_file(self, value):
        _validate_upload_size(value)
        if value.content_type not in ALLOWED_RECEIPT_CONTENT_TYPES:
            raise serializers.ValidationError("Receipts must be a JPEG, PNG, WEBP, or PDF file.")
        return value


class BankStatementImportSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankStatementImport
        fields = [
            "id", "file_name", "status", "imported_count", "skipped_count",
            "error_message", "imported_at",
        ]


class CSVImportRequestSerializer(serializers.Serializer):
    file = serializers.FileField()
    date_column = serializers.CharField()
    description_column = serializers.CharField()
    amount_column = serializers.CharField()

    def validate_file(self, value):
        _validate_upload_size(value)
        if not value.name.lower().endswith(".csv"):
            raise serializers.ValidationError("Please upload a .csv file.")
        return value
