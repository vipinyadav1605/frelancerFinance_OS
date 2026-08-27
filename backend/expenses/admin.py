from django.contrib import admin

from .models import BankStatementImport, Expense, ExpenseCategory


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "is_default"]
    search_fields = ["name", "user__email"]


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ["vendor_name", "user", "category", "amount", "expense_date", "source"]
    list_filter = ["source", "category"]
    search_fields = ["vendor_name", "user__email"]


@admin.register(BankStatementImport)
class BankStatementImportAdmin(admin.ModelAdmin):
    list_display = ["file_name", "user", "status", "imported_count", "skipped_count", "imported_at"]
    list_filter = ["status"]
