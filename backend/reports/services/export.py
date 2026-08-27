"""CSV/PDF export of a P&L snapshot, for the user's own CA (PRD Phase 3)."""

import csv
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from django.conf import settings

NAVY = colors.HexColor("#1a2b4c")
_FONTS_REGISTERED = False


def _ensure_unicode_fonts():
    """Same rationale as invoicing/services/pdf.py - see that file's docstring."""
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    ttf_dir = settings.BASE_DIR / "static" / "fonts"
    pdfmetrics.registerFont(TTFont("Helvetica", str(ttf_dir / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("Helvetica-Bold", str(ttf_dir / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFontFamily("Helvetica", normal="Helvetica", bold="Helvetica-Bold")
    _FONTS_REGISTERED = True


def export_profit_loss_csv(estimate, expenses) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Freelancer Finance OS - Profit & Loss Report"])
    writer.writerow(["Period", f"{estimate.period_start} to {estimate.period_end}"])
    writer.writerow([])
    writer.writerow(["Total Income (excl. GST)", f"{estimate.total_income}"])
    writer.writerow(["Total Expenses", f"{estimate.total_expense}"])
    writer.writerow(["Net Profit", f"{estimate.net_profit}"])
    writer.writerow([])
    writer.writerow(["GST Output Tax Collected", f"{estimate.gst_output_tax}"])
    writer.writerow(["GST Input Tax Credit (from expenses)", f"{estimate.gst_input_tax_credit}"])
    writer.writerow(["Estimated GST Liability", f"{estimate.estimated_gst_liability}"])
    writer.writerow([])
    writer.writerow([f"Financial Year ({estimate.financial_year_start} to {estimate.financial_year_end}) Gross Receipts",
                      f"{estimate.financial_year_gross_receipts}"])
    writer.writerow(["Estimated Income Tax (44ADA, rough estimate)", f"{estimate.estimated_income_tax}"])
    writer.writerow([])
    writer.writerow(["Expense Detail"])
    writer.writerow(["Date", "Vendor", "Category", "Amount", "GST Paid"])
    for exp in expenses:
        writer.writerow([exp.expense_date, exp.vendor_name, exp.category.name, exp.amount, exp.gst_paid])

    return buf.getvalue().encode("utf-8-sig")


def export_gstr1_csv(data) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["GSTR-1 Pre-fill Worksheet - Freelancer Finance OS"])
    writer.writerow(["Period", f"{data['period_start']} to {data['period_end']}"])
    writer.writerow(["This is a working paper to speed up manual GSTR-1 filing. Not a filed return - verify every figure before submitting on the GST portal."])
    writer.writerow([])

    def section(title, rows, totals):
        writer.writerow([title])
        writer.writerow([
            "Invoice No.", "Invoice Date", "Client Name", "Client GSTIN", "Place of Supply",
            "Invoice Value", "Taxable Value", "Rate %", "CGST", "SGST", "IGST", "LUT Reference",
        ])
        for r in rows:
            writer.writerow([
                r["invoice_number"], r["invoice_date"], r["client_name"], r["client_gstin"],
                r["place_of_supply"], r["invoice_value"], r["taxable_value"], r["rate_percent"],
                r["cgst_amount"], r["sgst_amount"], r["igst_amount"], r["lut_reference"],
            ])
        writer.writerow([
            f"{title} Total ({totals['count']} invoice(s))", "", "", "", "",
            totals["invoice_value"], totals["taxable_value"], "", "", "", "", "",
        ])
        writer.writerow([])

    section("B2B (registered domestic clients)", data["b2b"], data["b2b_totals"])
    section("B2C (unregistered domestic clients)", data["b2c"], data["b2c_totals"])
    section("Exports (zero-rated under LUT)", data["exports"], data["exports_totals"])

    return buf.getvalue().encode("utf-8-sig")


def export_profit_loss_pdf(estimate, expenses) -> bytes:
    _ensure_unicode_fonts()
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    small = ParagraphStyle("small", parent=normal, fontSize=8.5, leading=11, textColor=colors.HexColor("#555555"))
    title_style = ParagraphStyle("title", parent=styles["Heading1"], textColor=NAVY, fontSize=18)
    section_style = ParagraphStyle("section", parent=styles["Heading3"], textColor=NAVY, fontSize=12, spaceBefore=14)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm)
    story = [
        Paragraph("Profit &amp; Loss Report", title_style),
        Paragraph(f"Period: {estimate.period_start} to {estimate.period_end}", normal),
        Spacer(1, 0.4 * cm),
    ]

    def summary_table(rows):
        t = Table(rows, colWidths=[9 * cm, 4 * cm])
        t.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, -2), 0.4, colors.HexColor("#dddddd")),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ]))
        return t

    story.append(Paragraph("Profit &amp; Loss", section_style))
    story.append(summary_table([
        ["Total Income (excl. GST)", f"₹{estimate.total_income:,.2f}"],
        ["Total Expenses", f"₹{estimate.total_expense:,.2f}"],
        ["Net Profit", f"₹{estimate.net_profit:,.2f}"],
    ]))

    story.append(Paragraph("GST Estimate", section_style))
    story.append(summary_table([
        ["Output Tax Collected", f"₹{estimate.gst_output_tax:,.2f}"],
        ["Input Tax Credit (from expenses)", f"₹{estimate.gst_input_tax_credit:,.2f}"],
        ["Estimated GST Liability", f"₹{estimate.estimated_gst_liability:,.2f}"],
    ]))

    story.append(Paragraph(f"Income Tax Estimate (FY {estimate.financial_year_start} to {estimate.financial_year_end})", section_style))
    story.append(summary_table([
        ["Gross Receipts (full FY)", f"₹{estimate.financial_year_gross_receipts:,.2f}"],
        ["Estimated Income Tax (44ADA)", f"₹{estimate.estimated_income_tax:,.2f}"],
    ]))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        "Rough estimate only - assumes Section 44ADA presumptive taxation and new-regime slabs. "
        "Not filing advice; confirm with a CA before filing.", small,
    ))

    if expenses:
        story.append(Paragraph("Expense Detail", section_style))
        rows = [["Date", "Vendor", "Category", "Amount", "GST Paid"]]
        for exp in expenses:
            rows.append([str(exp.expense_date), exp.vendor_name, exp.category.name, f"{exp.amount:,.2f}", f"{exp.gst_paid:,.2f}"])
        table = Table(rows, colWidths=[2.2 * cm, 5.0 * cm, 3.8 * cm, 2.3 * cm, 2.3 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("ALIGN", (3, 1), (4, -1), "RIGHT"),
        ]))
        story.append(table)

    doc.build(story)
    return buf.getvalue()
