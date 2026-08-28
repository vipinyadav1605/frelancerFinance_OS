"""Phase 6 "settings": lets a user download everything - builds trust that
their data isn't locked into this one app, independent of the CA-facing P&L/
GSTR-1 exports in reports/services/export.py (which summarize, not dump raw
records)."""

import csv
import io
import zipfile

from clients.models import Client
from expenses.models import Expense
from invoicing.models import Invoice


def _write_csv(writer_rows_fn) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer_rows_fn(writer)
    return buf.getvalue().encode("utf-8-sig")


def _clients_csv(user) -> bytes:
    def rows(writer):
        writer.writerow(["Name", "Email", "Country", "State", "GSTIN", "International", "Created At"])
        for c in Client.objects.filter(user=user):
            writer.writerow([c.name, c.email, c.country, c.state, c.gstin, c.is_international, c.created_at])
    return _write_csv(rows)


def _invoices_csv(user) -> bytes:
    def rows(writer):
        writer.writerow([
            "Invoice Number", "Client", "Issue Date", "Due Date", "Currency", "Subtotal",
            "CGST", "SGST", "IGST", "Total", "Status", "Paid At",
        ])
        for inv in Invoice.objects.filter(user=user):
            writer.writerow([
                inv.invoice_number, inv.client_name_snapshot, inv.issue_date, inv.due_date, inv.currency,
                inv.subtotal, inv.cgst_amount, inv.sgst_amount, inv.igst_amount, inv.total_amount,
                inv.status, inv.paid_at,
            ])
    return _write_csv(rows)


def _expenses_csv(user) -> bytes:
    def rows(writer):
        writer.writerow(["Date", "Vendor", "Category", "Amount", "GST Paid", "Source", "Notes"])
        for exp in Expense.objects.filter(user=user).select_related("category"):
            writer.writerow([
                exp.expense_date, exp.vendor_name, exp.category.name, exp.amount,
                exp.gst_paid, exp.source, exp.notes,
            ])
    return _write_csv(rows)


def export_all_user_data_zip(user) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("clients.csv", _clients_csv(user))
        zf.writestr("invoices.csv", _invoices_csv(user))
        zf.writestr("expenses.csv", _expenses_csv(user))
    return buf.getvalue()
