"""
Combines invoicing (income) and expenses to produce the P&L + GST + income
tax snapshot that is the core 'OS' value proposition (Document 1, Phase 3).

Key accounting decision, worth stating explicitly: income is based on each
paid invoice's SUBTOTAL (pre-GST), not its tax-inclusive total. GST collected
from a client is money held on behalf of the government, not the
freelancer's income - counting it as income would overstate profit and
overstate 44ADA gross receipts. The same logic applies to GST paid on
expenses (see expenses.models.Expense.gst_paid): that portion isn't a real
business cost, it's a potential input tax credit against GST owed.

"Income" is recognized on payment date (paid_at), matching how a freelancer
actually experiences cash flow - not on invoice issue date.
"""

from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Sum

from expenses.models import Expense
from invoicing.models import Invoice, InvoiceStatus
from reports.models import TaxEstimate

from .income_tax import estimate_income_tax, financial_year_bounds

TWO_PLACES = Decimal("0.01")


def _round(value) -> Decimal:
    return Decimal(value or 0).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _paid_invoices_in_range(user, start, end):
    return Invoice.objects.filter(user=user, status=InvoiceStatus.PAID, paid_at__date__gte=start, paid_at__date__lte=end)


def _gross_receipts_inr(invoices) -> Decimal:
    total = Decimal("0")
    for inv in invoices:
        total += inv.subtotal * inv.exchange_rate_to_inr
    return total


def _gst_output_tax_inr(invoices) -> Decimal:
    total = Decimal("0")
    for inv in invoices:
        total += (inv.cgst_amount + inv.sgst_amount + inv.igst_amount) * inv.exchange_rate_to_inr
    return total


def compute_profit_loss(user, period_start, period_end) -> TaxEstimate:
    paid_invoices = list(_paid_invoices_in_range(user, period_start, period_end))

    total_income = _round(_gross_receipts_inr(paid_invoices))
    gst_output_tax = _round(_gst_output_tax_inr(paid_invoices))

    expenses_in_range = Expense.objects.filter(
        user=user, expense_date__gte=period_start, expense_date__lte=period_end
    )
    expense_totals = expenses_in_range.aggregate(
        total_amount=Sum("amount"), total_gst_paid=Sum("gst_paid")
    )
    total_expense = _round(expense_totals["total_amount"])
    gst_input_tax_credit = _round(expense_totals["total_gst_paid"])

    net_profit = _round(total_income - total_expense)
    estimated_gst_liability = _round(max(gst_output_tax - gst_input_tax_credit, Decimal("0")))

    fy_start, fy_end = financial_year_bounds(period_end)
    fy_gross_receipts = _round(_gross_receipts_inr(_paid_invoices_in_range(user, fy_start, fy_end)))
    income_tax_result = estimate_income_tax(fy_gross_receipts)

    estimate, _ = TaxEstimate.objects.update_or_create(
        user=user, period_start=period_start, period_end=period_end,
        defaults=dict(
            total_income=total_income,
            total_expense=total_expense,
            net_profit=net_profit,
            gst_output_tax=gst_output_tax,
            gst_input_tax_credit=gst_input_tax_credit,
            estimated_gst_liability=estimated_gst_liability,
            financial_year_start=fy_start,
            financial_year_end=fy_end,
            financial_year_gross_receipts=fy_gross_receipts,
            estimated_income_tax=income_tax_result["estimated_total_tax"],
        ),
    )
    # Stashed for the view to build a richer response without recomputing.
    estimate._income_tax_detail = income_tax_result
    return estimate
