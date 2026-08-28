from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from config.pagination import StandardResultsPagination
from integrations.services.webhooks import send_webhook_event

from .models import BankStatementImport, Expense, ExpenseCategory
from .serializers import (
    BankStatementImportSerializer, CSVImportRequestSerializer, ExpenseCategorySerializer,
    ExpenseSerializer,
)
from .services.csv_import import import_bank_statement_csv


class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "head", "options"]
    serializer_class = ExpenseCategorySerializer

    def get_queryset(self):
        return ExpenseCategory.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    pagination_class = StandardResultsPagination

    def get_queryset(self):
        qs = Expense.objects.filter(user=self.request.user)
        params = self.request.query_params
        if category_id := params.get("category"):
            qs = qs.filter(category_id=category_id)
        if date_from := params.get("date_from"):
            qs = qs.filter(expense_date__gte=date_from)
        if date_to := params.get("date_to"):
            qs = qs.filter(expense_date__lte=date_to)
        return qs

    def perform_create(self, serializer):
        expense = serializer.save(user=self.request.user, source="manual")
        send_webhook_event(self.request.user, "expense.created", {
            "vendor_name": expense.vendor_name,
            "amount": str(expense.amount),
            "category": expense.category.name,
            "expense_date": str(expense.expense_date),
        })


class BankStatementImportListView(APIView):
    def get(self, request):
        imports = BankStatementImport.objects.filter(user=request.user)
        return Response(BankStatementImportSerializer(imports, many=True).data)


class ImportBankStatementCSVView(APIView):
    """FR (Phase 2): CSV bank/UPI statement upload with column mapping + auto-categorization."""

    def post(self, request):
        serializer = CSVImportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        import_record = import_bank_statement_csv(
            user=request.user,
            uploaded_file=data["file"],
            date_column=data["date_column"],
            description_column=data["description_column"],
            amount_column=data["amount_column"],
        )

        if import_record.status == "failed":
            return Response(BankStatementImportSerializer(import_record).data, status=status.HTTP_400_BAD_REQUEST)

        expenses = Expense.objects.filter(bank_statement_import=import_record)
        return Response({
            "import": BankStatementImportSerializer(import_record).data,
            "expenses": ExpenseSerializer(expenses, many=True, context={"request": request}).data,
        }, status=status.HTTP_201_CREATED)
