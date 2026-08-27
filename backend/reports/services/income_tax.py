"""
Rough income tax estimate under Section 44ADA presumptive taxation, which is
what most freelance consultants/professionals in India use (PRD Phase 3:
"shown as an estimate, not filing advice").

IMPORTANT CAVEATS baked into this module on purpose:
- Slab rates and the Section 87A rebate threshold change with each Union
  Budget. The constants below reflect the new tax regime for FY 2025-26
  (AY 2026-27) as of when this was written - update them when rates change,
  and never present this as authoritative. It ignores other income, other
  deductions (80C etc.), and old-vs-new-regime choice entirely.
- 44ADA gross receipts eligibility is capped at Rs 50 lakh (or Rs 75 lakh if
  95%+ of receipts are digital) - this module always uses Rs 50 lakh since
  we don't track payment-mode mix.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

PRESUMPTIVE_PROFIT_RATE = Decimal("0.50")
PRESUMPTIVE_ELIGIBILITY_LIMIT = Decimal("5000000")  # Rs 50 lakh gross receipts

# (upper bound of slab, rate) - FY 2025-26 new tax regime.
SLABS = [
    (Decimal("400000"), Decimal("0.00")),
    (Decimal("800000"), Decimal("0.05")),
    (Decimal("1200000"), Decimal("0.10")),
    (Decimal("1600000"), Decimal("0.15")),
    (Decimal("2000000"), Decimal("0.20")),
    (Decimal("2400000"), Decimal("0.25")),
    (None, Decimal("0.30")),  # anything above the last bound
]

REBATE_87A_TAXABLE_INCOME_LIMIT = Decimal("1200000")  # tax becomes nil at/below this
CESS_RATE = Decimal("0.04")

TWO_PLACES = Decimal("0.01")


def _round(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def financial_year_bounds(for_date: date) -> tuple[date, date]:
    """India's financial year runs 1 April - 31 March."""
    if for_date.month >= 4:
        start = date(for_date.year, 4, 1)
        end = date(for_date.year + 1, 3, 31)
    else:
        start = date(for_date.year - 1, 4, 1)
        end = date(for_date.year, 3, 31)
    return start, end


def _slab_tax(taxable_income: Decimal) -> Decimal:
    tax = Decimal("0")
    lower_bound = Decimal("0")
    for upper_bound, rate in SLABS:
        slab_top = upper_bound if upper_bound is not None else taxable_income
        slab_amount = min(taxable_income, slab_top) - lower_bound
        if slab_amount > 0:
            tax += slab_amount * rate
        if upper_bound is not None and taxable_income <= upper_bound:
            break
        lower_bound = slab_top
    return tax


def estimate_income_tax(gross_receipts: Decimal) -> dict:
    """gross_receipts should already exclude GST collected (see profit_loss.py)."""
    is_44ada_eligible = gross_receipts <= PRESUMPTIVE_ELIGIBILITY_LIMIT
    presumptive_taxable_income = _round(gross_receipts * PRESUMPTIVE_PROFIT_RATE)

    base_tax = _slab_tax(presumptive_taxable_income)
    rebate_applied = presumptive_taxable_income <= REBATE_87A_TAXABLE_INCOME_LIMIT
    if rebate_applied:
        base_tax = Decimal("0")

    cess = _round(base_tax * CESS_RATE)
    total_tax = _round(base_tax + cess)

    return {
        "gross_receipts": _round(gross_receipts),
        "is_44ada_eligible": is_44ada_eligible,
        "presumptive_taxable_income": presumptive_taxable_income,
        "rebate_87a_applied": rebate_applied,
        "base_tax": _round(base_tax),
        "cess": cess,
        "estimated_total_tax": total_tax,
        "disclaimer": (
            "Rough estimate only, assuming Section 44ADA presumptive taxation "
            "(50% of gross receipts as taxable income) and the new tax regime "
            "slabs for FY 2025-26. Ignores other income, deductions, and regime "
            "choice. Not filing advice - confirm with a CA before filing."
        ),
    }
