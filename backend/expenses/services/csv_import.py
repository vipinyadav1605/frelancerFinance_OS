"""
CSV bank/UPI statement import with simple keyword-based auto-categorization
(PRD Phase 2: "CSV bank/UPI statement upload with column mapping +
auto-categorization suggestions - simple keyword rules to start").

The caller supplies which CSV column holds the date, description, and debit
amount (the "column mapping") - this keeps the parser simple while still
working across the different export formats banks use.
"""

import csv
import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from expenses.constants import CATEGORY_KEYWORDS
from expenses.models import (
    BankStatementImport, BankStatementImportStatus, Expense, ExpenseCategory, ExpenseSource,
)

DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%d %b %Y", "%d-%b-%Y"]


def _parse_date(raw: str):
    raw = raw.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _parse_amount(raw: str):
    if not raw:
        return None
    cleaned = re.sub(r"[^\d.\-()]", "", raw.strip())
    if not cleaned:
        return None
    is_negative_paren = cleaned.startswith("(") and cleaned.endswith(")")
    cleaned = cleaned.strip("()")
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return None
    if is_negative_paren:
        value = -value
    return abs(value) if value != 0 else None


def _categorize(description: str, categories_by_name: dict) -> ExpenseCategory:
    description_lower = description.lower()
    for category_name, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in description_lower for keyword in keywords):
            category = categories_by_name.get(category_name)
            if category:
                return category
    return categories_by_name.get("Other")


def import_bank_statement_csv(*, user, uploaded_file, date_column, description_column, amount_column) -> BankStatementImport:
    import_record = BankStatementImport.objects.create(
        user=user, file_name=uploaded_file.name, status=BankStatementImportStatus.PROCESSING,
    )

    try:
        text_stream = io.TextIOWrapper(uploaded_file.file, encoding="utf-8-sig")
        reader = csv.DictReader(text_stream)

        if reader.fieldnames is None or not {date_column, description_column, amount_column}.issubset(set(reader.fieldnames)):
            import_record.status = BankStatementImportStatus.FAILED
            import_record.error_message = (
                f"CSV is missing one or more mapped columns. Found columns: {reader.fieldnames}"
            )
            import_record.save()
            return import_record

        categories_by_name = {c.name: c for c in ExpenseCategory.objects.filter(user=user)}
        if "Other" not in categories_by_name:
            categories_by_name["Other"], _ = ExpenseCategory.objects.get_or_create(
                user=user, name="Other", defaults={"is_default": True}
            )

        imported, skipped = 0, 0
        new_expenses = []
        for row in reader:
            expense_date = _parse_date(row.get(date_column, ""))
            amount = _parse_amount(row.get(amount_column, ""))
            description = (row.get(description_column) or "").strip()

            if not expense_date or amount is None or not description:
                skipped += 1
                continue

            category = _categorize(description, categories_by_name)
            new_expenses.append(Expense(
                user=user,
                category=category,
                vendor_name=description[:255],
                amount=amount,
                expense_date=expense_date,
                source=ExpenseSource.CSV_IMPORT,
                bank_statement_import=import_record,
            ))
            imported += 1

        Expense.objects.bulk_create(new_expenses)
        import_record.imported_count = imported
        import_record.skipped_count = skipped
        import_record.status = BankStatementImportStatus.COMPLETED
        import_record.save()

    except Exception as exc:  # noqa: BLE001 - surfaced to the user via the import record
        import_record.status = BankStatementImportStatus.FAILED
        import_record.error_message = str(exc)
        import_record.save()

    return import_record
