"""
GST-compliant invoice PDF generation (FR-5), using reportlab (pure Python,
no system dependencies - important given the solo/low-budget constraints
in Document 1).
"""

import io

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

NAVY = colors.HexColor("#1a2b4c")

CURRENCY_SYMBOLS = {"INR": "\u20b9", "USD": "$", "EUR": "\u20ac", "GBP": "\u00a3"}

_FONTS_REGISTERED = False


def _ensure_unicode_fonts():
    """
    Registers a Unicode-capable font (DejaVu Sans, bundled under
    backend/static/fonts/ so this works identically on Windows dev and
    Linux hosting) under the standard Helvetica names so the rupee sign
    and other non-Latin1 glyphs render correctly. Must also re-register
    the font family mapping, otherwise reportlab's inline <b>/<i> tags
    silently stop bolding/italicizing (this bit the roadmap/PRD PDFs
    during development - see Document 2 for the writeup).
    """
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return

    ttf_dir = settings.BASE_DIR / "static" / "fonts"
    pdfmetrics.registerFont(TTFont("Helvetica", str(ttf_dir / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("Helvetica-Bold", str(ttf_dir / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("Helvetica-Oblique", str(ttf_dir / "DejaVuSans-Oblique.ttf")))
    pdfmetrics.registerFont(TTFont("Helvetica-BoldOblique", str(ttf_dir / "DejaVuSans-BoldOblique.ttf")))
    pdfmetrics.registerFontFamily(
        "Helvetica", normal="Helvetica", bold="Helvetica-Bold",
        italic="Helvetica-Oblique", boldItalic="Helvetica-BoldOblique",
    )
    _FONTS_REGISTERED = True


def _money(amount, currency):
    symbol = CURRENCY_SYMBOLS.get(currency, currency + " ")
    return f"{symbol}{amount:,.2f}"


def generate_invoice_pdf(invoice) -> bytes:
    _ensure_unicode_fonts()
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    small = ParagraphStyle("small", parent=normal, fontSize=8.5, leading=11)
    title_style = ParagraphStyle("title", parent=styles["Heading1"], textColor=NAVY, fontSize=20)

    profile = invoice.user.business_profile
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm,
    )
    story = []

    header = Table(
        [[
            Paragraph(f"<b>{profile.business_name}</b><br/>{profile.address}<br/>"
                      f"{profile.state}, India"
                      + (f"<br/>GSTIN: {profile.gstin}" if profile.gstin else ""), small),
            Paragraph(f"<font size=18 color='#1a2b4c'><b>INVOICE</b></font><br/>"
                      f"<b>{invoice.invoice_number}</b><br/>"
                      f"Issue date: {invoice.issue_date}<br/>Due date: {invoice.due_date}", normal),
        ]],
        colWidths=[9 * cm, 8 * cm],
    )
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(header)
    story.append(Spacer(1, 0.6 * cm))

    bill_to = (
        f"<b>Bill To</b><br/>{invoice.client_name_snapshot}<br/>"
        f"{invoice.client_address_snapshot}<br/>{invoice.client_country_snapshot}"
    )
    if invoice.client_gstin_snapshot:
        bill_to += f"<br/>GSTIN: {invoice.client_gstin_snapshot}"
    story.append(Paragraph(bill_to, normal))
    if invoice.tax_type == "EXPORT_ZERO_RATED":
        story.append(Paragraph(
            f"<i>Export of services - zero-rated under LUT"
            + (f" (ARN: {invoice.lut_reference})" if invoice.lut_reference else "")
            + ".</i>", small,
        ))
    story.append(Spacer(1, 0.5 * cm))

    rows = [["Description", "HSN/SAC", "Qty", "Unit Price", "Tax %", "Amount"]]
    for item in invoice.items.all():
        rows.append([
            item.description, item.hsn_sac_code or "-", f"{item.quantity:g}",
            _money(item.unit_price, invoice.currency), f"{item.tax_rate_percent:g}%",
            _money(item.amount, invoice.currency),
        ])
    items_table = Table(rows, colWidths=[5.6 * cm, 2.2 * cm, 1.4 * cm, 2.8 * cm, 1.8 * cm, 2.6 * cm])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 0.4 * cm))

    totals_rows = [["Subtotal", _money(invoice.subtotal, invoice.currency)]]
    if invoice.tax_type == "CGST_SGST":
        totals_rows.append(["CGST", _money(invoice.cgst_amount, invoice.currency)])
        totals_rows.append(["SGST", _money(invoice.sgst_amount, invoice.currency)])
    elif invoice.tax_type == "IGST":
        totals_rows.append(["IGST", _money(invoice.igst_amount, invoice.currency)])
    totals_rows.append(["Total", _money(invoice.total_amount, invoice.currency)])

    totals_table = Table(totals_rows, colWidths=[4 * cm, 3.5 * cm], hAlign="RIGHT")
    totals_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(totals_table)

    if invoice.currency != "INR":
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph(
            f"Exchange rate at issue: 1 {invoice.currency} = "
            f"\u20b9{invoice.exchange_rate_to_inr} (for reference only).", small,
        ))

    doc.build(story)
    return buf.getvalue()
