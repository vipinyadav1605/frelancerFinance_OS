"""
GSTR-1 pre-fill worksheet (Phase 4).

Unlike the P&L report (which is cash-basis - it counts an invoice once it's
paid), GST liability is accrual-basis: it arises when an invoice is issued,
regardless of whether the client has paid yet. So this groups by issue_date,
not paid_at, and excludes drafts (a draft was never actually issued).

Invoices are bucketed the way the GSTN portal itself buckets them for filing:
- B2B: domestic client with a GSTIN on file (recipient can claim input credit)
- B2C: domestic client with no GSTIN on file
- Exports: international client, zero-rated under LUT
"""

from decimal import Decimal

from invoicing.models import Invoice, TaxType


def _effective_rate_percent(invoice) -> Decimal:
    if invoice.subtotal == 0:
        return Decimal("0")
    total_tax = invoice.cgst_amount + invoice.sgst_amount + invoice.igst_amount
    return (total_tax / invoice.subtotal * 100).quantize(Decimal("0.01"))


def _row(invoice):
    return {
        "invoice_number": invoice.invoice_number,
        "invoice_date": invoice.issue_date,
        "client_name": invoice.client_name_snapshot,
        "client_gstin": invoice.client_gstin_snapshot,
        "place_of_supply": invoice.client_state_snapshot or invoice.client_country_snapshot,
        "invoice_value": invoice.total_amount,
        "taxable_value": invoice.subtotal,
        "rate_percent": _effective_rate_percent(invoice),
        "cgst_amount": invoice.cgst_amount,
        "sgst_amount": invoice.sgst_amount,
        "igst_amount": invoice.igst_amount,
        "lut_reference": invoice.lut_reference,
    }


def compute_gstr1_prefill(user, period_start, period_end):
    invoices = (
        Invoice.objects.filter(user=user, issue_date__gte=period_start, issue_date__lte=period_end)
        .exclude(status="draft")
        .order_by("issue_date")
    )

    b2b, b2c, exports = [], [], []
    for invoice in invoices:
        row = _row(invoice)
        if invoice.tax_type == TaxType.EXPORT_ZERO_RATED:
            exports.append(row)
        elif invoice.client_gstin_snapshot:
            b2b.append(row)
        else:
            b2c.append(row)

    def totals(rows):
        return {
            "count": len(rows),
            "taxable_value": sum((r["taxable_value"] for r in rows), Decimal("0")),
            "tax_amount": sum((r["cgst_amount"] + r["sgst_amount"] + r["igst_amount"] for r in rows), Decimal("0")),
            "invoice_value": sum((r["invoice_value"] for r in rows), Decimal("0")),
        }

    return {
        "period_start": period_start,
        "period_end": period_end,
        "b2b": b2b,
        "b2c": b2c,
        "exports": exports,
        "b2b_totals": totals(b2b),
        "b2c_totals": totals(b2c),
        "exports_totals": totals(exports),
    }
