from datetime import date
from decimal import Decimal

from django.test import TestCase

from reports.services.income_tax import estimate_income_tax, financial_year_bounds


class FinancialYearBoundsTests(TestCase):
    def test_date_in_second_half_of_calendar_year(self):
        start, end = financial_year_bounds(date(2026, 8, 23))
        self.assertEqual(start, date(2026, 4, 1))
        self.assertEqual(end, date(2027, 3, 31))

    def test_date_in_first_quarter_of_calendar_year(self):
        start, end = financial_year_bounds(date(2026, 2, 15))
        self.assertEqual(start, date(2025, 4, 1))
        self.assertEqual(end, date(2026, 3, 31))


class EstimateIncomeTaxTests(TestCase):
    def test_low_income_gets_full_rebate(self):
        # Gross receipts 10L -> presumptive taxable income 5L, well under the 12L rebate limit.
        result = estimate_income_tax(Decimal("1000000"))
        self.assertTrue(result["is_44ada_eligible"])
        self.assertEqual(result["presumptive_taxable_income"], Decimal("500000.00"))
        self.assertTrue(result["rebate_87a_applied"])
        self.assertEqual(result["estimated_total_tax"], Decimal("0.00"))

    def test_income_just_above_rebate_threshold_is_taxed(self):
        # Gross receipts 26L -> presumptive taxable income 13L, just above the 12L rebate limit.
        result = estimate_income_tax(Decimal("2600000"))
        self.assertFalse(result["rebate_87a_applied"])
        self.assertGreater(result["estimated_total_tax"], Decimal("0"))

    def test_ineligible_for_44ada_above_50_lakh_receipts(self):
        result = estimate_income_tax(Decimal("6000000"))
        self.assertFalse(result["is_44ada_eligible"])

    def test_slab_tax_calculation_matches_expected(self):
        # Presumptive taxable income of 20L (from 40L gross receipts):
        # 0-4L: 0%, 4-8L: 5% = 20000, 8-12L: 10% = 40000, 12-16L: 15% = 60000, 16-20L: 20% = 80000
        # base tax = 200000, above rebate threshold so no rebate.
        result = estimate_income_tax(Decimal("4000000"))
        self.assertEqual(result["presumptive_taxable_income"], Decimal("2000000.00"))
        self.assertEqual(result["base_tax"], Decimal("200000.00"))
        expected_cess = Decimal("200000.00") * Decimal("0.04")
        self.assertEqual(result["cess"], expected_cess)
        self.assertEqual(result["estimated_total_tax"], Decimal("200000.00") + expected_cess)
