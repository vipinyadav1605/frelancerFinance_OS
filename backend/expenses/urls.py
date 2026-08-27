from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    BankStatementImportListView, ExpenseCategoryViewSet, ExpenseViewSet,
    ImportBankStatementCSVView,
)

router = DefaultRouter()
router.register("expense-categories", ExpenseCategoryViewSet, basename="expense-category")
router.register("expenses", ExpenseViewSet, basename="expense")

# The explicit "import-csv" path must be listed BEFORE router.urls, otherwise
# the router's /expenses/{pk}/ pattern greedily matches "import-csv" as a pk.
urlpatterns = [
    path("bank-statement-imports/", BankStatementImportListView.as_view(), name="bank-statement-imports"),
    path("expenses/import-csv/", ImportBankStatementCSVView.as_view(), name="import-bank-statement-csv"),
] + router.urls
