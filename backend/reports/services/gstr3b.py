"""
GSTR-3B summary (the monthly/quarterly self-assessed summary return, filed
before the detailed GSTR-1). Built on top of the same accrual-basis invoice
buckets as gstr1.py (GST liability arises on issue, not on payment) plus
GST paid on expenses in the same period as the eligible input tax credit.

This mirrors the return's actual table structure (simplified to what a
freelancer with domestic B2B/B2C clients and zero-rated LUT exports
actually needs - no reverse charge, no exempt/nil-rated supplies):

- 3.1(a) Outward taxable supplies (domestic B2B + B2C)
- 3.1(b) Outward zero-rated supplies (LUT exports)
- 4    Eligible ITC (from GST paid on expenses)
- 5    Net tax payable in cash, after applying ITC

This is a pre-filing worksheet, not a filed return - always verify against
the GST portal before filing.
"""

from decimal import Decimal

from django.db.models import Sum

from expenses.models import Expense

from .gstr1 import compute_gstr1_prefill


def _sum_field(rows, field) -> Decimal:
    return sum((r[field] for r in rows), Decimal("0"))


def compute_gstr3b_summary(user, period_start, period_end):
    gstr1 = compute_gstr1_prefill(user, period_start, period_end)
    domestic_rows = gstr1["b2b"] + gstr1["b2c"]

    integrated_tax = _sum_field(domestic_rows, "igst_amount")
    central_tax = _sum_field(domestic_rows, "cgst_amount")
    state_tax = _sum_field(domestic_rows, "sgst_amount")
    output_tax_total = integrated_tax + central_tax + state_tax

    eligible_itc = Expense.objects.filter(
        user=user, expense_date__gte=period_start, expense_date__lte=period_end
    ).aggregate(total=Sum("gst_paid"))["total"] or Decimal("0")

    return {
        "period_start": period_start,
        "period_end": period_end,
        "outward_taxable_supplies": {
            "taxable_value": _sum_field(domestic_rows, "taxable_value"),
            "integrated_tax": integrated_tax,
            "central_tax": central_tax,
            "state_tax": state_tax,
        },
        "outward_zero_rated_supplies": {
            "taxable_value": gstr1["exports_totals"]["taxable_value"],
        },
        "eligible_itc": eligible_itc,
        "net_tax_payable": max(output_tax_total - eligible_itc, Decimal("0")),
        "itc_carried_forward": max(eligible_itc - output_tax_total, Decimal("0")),
    }
