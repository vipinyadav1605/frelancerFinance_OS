"""
Tax determination and calculation for invoices (FR-4).

This is the most trust-critical piece of the product (PRD, Section 7.1) so
the logic is kept in one small, independently-testable module rather than
scattered across views/serializers.
"""

from decimal import ROUND_HALF_UP, Decimal

from invoicing.models import TaxType

TWO_PLACES = Decimal("0.01")


def _round(value):
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def determine_tax_type(business_state: str, client) -> str:
    """
    FR-4 acceptance criteria:
    - international client -> export, zero-rated GST (LUT)
    - domestic client, same state as the business -> CGST + SGST
    - domestic client, different state -> IGST
    """
    if client.is_international:
        return TaxType.EXPORT_ZERO_RATED
    if client.state == business_state:
        return TaxType.CGST_SGST
    return TaxType.IGST


def calculate_invoice_totals(items: list[dict], tax_type: str) -> dict:
    """
    items: list of {"quantity": Decimal, "unit_price": Decimal, "tax_rate_percent": Decimal}
    Returns subtotal/cgst/sgst/igst/total, each a Decimal rounded to 2 places.
    """
    subtotal = sum((Decimal(i["quantity"]) * Decimal(i["unit_price"]) for i in items), Decimal("0"))

    if tax_type == TaxType.EXPORT_ZERO_RATED:
        cgst = sgst = igst = Decimal("0")
    else:
        total_tax = sum(
            (
                Decimal(i["quantity"]) * Decimal(i["unit_price"]) * Decimal(i["tax_rate_percent"]) / Decimal("100")
                for i in items
            ),
            Decimal("0"),
        )
        if tax_type == TaxType.CGST_SGST:
            cgst = sgst = total_tax / 2
            igst = Decimal("0")
        elif tax_type == TaxType.IGST:
            cgst = sgst = Decimal("0")
            igst = total_tax
        else:
            raise ValueError(f"Unknown tax_type: {tax_type}")

    total = subtotal + cgst + sgst + igst
    return {
        "subtotal": _round(subtotal),
        "cgst_amount": _round(cgst),
        "sgst_amount": _round(sgst),
        "igst_amount": _round(igst),
        "total_amount": _round(total),
    }
