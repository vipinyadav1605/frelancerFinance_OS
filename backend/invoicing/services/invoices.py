"""Orchestrates creating an invoice: tax determination, numbering, totals, snapshot."""

from django.core.files.base import ContentFile
from django.db import transaction

from invoicing.models import Invoice, InvoiceItem

from .numbering import next_invoice_number
from .pdf import generate_invoice_pdf
from .tax import calculate_invoice_totals, determine_tax_type


@transaction.atomic
def create_invoice(*, user, client, issue_date, due_date, currency, exchange_rate_to_inr, items_data):
    profile = user.business_profile
    tax_type = determine_tax_type(profile.state, client)
    totals = calculate_invoice_totals(items_data, tax_type)

    invoice = Invoice.objects.create(
        user=user,
        client=client,
        client_name_snapshot=client.name,
        client_email_snapshot=client.email,
        client_address_snapshot=client.billing_address,
        client_country_snapshot=client.country,
        client_state_snapshot=client.state,
        client_gstin_snapshot=client.gstin,
        invoice_number=next_invoice_number(user),
        issue_date=issue_date,
        due_date=due_date,
        currency=currency,
        exchange_rate_to_inr=exchange_rate_to_inr,
        tax_type=tax_type,
        lut_reference=profile.lut_reference if tax_type == "EXPORT_ZERO_RATED" else "",
        **totals,
    )

    InvoiceItem.objects.bulk_create([
        InvoiceItem(
            invoice=invoice,
            description=item["description"],
            hsn_sac_code=item.get("hsn_sac_code", ""),
            quantity=item["quantity"],
            unit_price=item["unit_price"],
            tax_rate_percent=item.get("tax_rate_percent", 0),
            amount=item["quantity"] * item["unit_price"],
        )
        for item in items_data
    ])

    # FR-5: every saved invoice produces a compliant PDF immediately.
    pdf_bytes = generate_invoice_pdf(invoice)
    invoice.pdf_file.save(f"{invoice.invoice_number}.pdf", ContentFile(pdf_bytes), save=True)

    return invoice
