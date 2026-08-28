"""Dashboard chart data - visual trends on top of the numeric P&L report."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import F, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from expenses.models import Expense
from invoicing.models import Invoice, InvoiceStatus

TWO_PLACES = Decimal("0.01")


def _round(value) -> Decimal:
    return Decimal(value or 0).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _months_ago(months: int) -> date:
    today = timezone.localdate()
    month_index = today.month - 1 - months
    year = today.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def monthly_revenue_trend(user, months: int = 12) -> list[dict]:
    """Income (paid invoices, pre-GST subtotal in INR) and expenses per month, oldest first."""
    start = _months_ago(months - 1)

    income_by_month = {
        row["month"].strftime("%Y-%m"): row["total"]
        for row in Invoice.objects.filter(user=user, status=InvoiceStatus.PAID, paid_at__date__gte=start)
        .annotate(month=TruncMonth("paid_at"))
        .values("month")
        .annotate(total=Sum(F("subtotal") * F("exchange_rate_to_inr")))
    }
    expense_by_month = {
        row["month"].strftime("%Y-%m"): row["total"]
        for row in Expense.objects.filter(user=user, expense_date__gte=start)
        .annotate(month=TruncMonth("expense_date"))
        .values("month")
        .annotate(total=Sum("amount"))
    }

    trend = []
    cursor = start
    for _ in range(months):
        key = cursor.strftime("%Y-%m")
        trend.append({
            "month": key,
            "total_income": _round(income_by_month.get(key, 0)),
            "total_expense": _round(expense_by_month.get(key, 0)),
        })
        month_index = cursor.month + 1
        cursor = date(cursor.year + (month_index - 1) // 12, (month_index - 1) % 12 + 1, 1)
    return trend


def expense_breakdown_by_category(user, period_start, period_end) -> list[dict]:
    rows = (
        Expense.objects.filter(user=user, expense_date__gte=period_start, expense_date__lte=period_end)
        .values("category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    return [{"category": row["category__name"], "total": _round(row["total"])} for row in rows]


def top_clients_by_revenue(user, period_start, period_end, limit: int = 5) -> list[dict]:
    rows = (
        Invoice.objects.filter(
            user=user, status=InvoiceStatus.PAID, paid_at__date__gte=period_start, paid_at__date__lte=period_end,
        )
        .values("client_name_snapshot")
        .annotate(total=Sum(F("subtotal") * F("exchange_rate_to_inr")))
        .order_by("-total")[:limit]
    )
    return [{"client_name": row["client_name_snapshot"], "total": _round(row["total"])} for row in rows]
