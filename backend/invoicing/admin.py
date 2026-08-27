from django.contrib import admin

from .models import Invoice, InvoiceItem, Payment


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ["invoice_number", "user", "client_name_snapshot", "status", "total_amount", "issue_date", "due_date"]
    list_filter = ["status", "tax_type", "currency"]
    search_fields = ["invoice_number", "client_name_snapshot", "user__email"]
    inlines = [InvoiceItemInline, PaymentInline]
