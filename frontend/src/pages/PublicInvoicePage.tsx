import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getPublicInvoice } from "../api/endpoints";
import type { PublicInvoice } from "../types";
import { extractErrorMessage } from "../utils/errors";

const CURRENCY_SYMBOLS: Record<string, string> = { INR: "₹", USD: "$", EUR: "€", GBP: "£" };

function money(amount: string, currency: string) {
  return `${CURRENCY_SYMBOLS[currency] ?? currency + " "}${Number(amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
}

const STATUS_BADGE: Record<string, string> = {
  draft: "badge-grey", sent: "badge-blue", paid: "badge-green", overdue: "badge-red",
};

export function PublicInvoicePage() {
  const { token } = useParams<{ token: string }>();
  const [invoice, setInvoice] = useState<PublicInvoice | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    getPublicInvoice(token)
      .then(setInvoice)
      .catch((err) => setError(extractErrorMessage(err, "This invoice link is invalid.")))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) return <div className="page-loading"><span className="spinner-lg" /> Loading...</div>;

  if (error || !invoice) {
    return (
      <div className="page">
        <div className="alert alert-error">{error || "This invoice link is invalid."}</div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header page-header-row">
        <div>
          <h1>{invoice.invoice_number}</h1>
          <p className="page-subtitle">From {invoice.business_name}</p>
        </div>
        <span className={`badge badge-lg ${STATUS_BADGE[invoice.status] ?? "badge-grey"}`}>{invoice.status}</span>
      </div>

      <div className="card">
        <div className="invoice-detail-grid">
          <div>
            <h4>Billed To</h4>
            <p>
              {invoice.client_name_snapshot}<br />
              {invoice.client_address_snapshot}<br />
              {invoice.client_country_snapshot}
            </p>
            {invoice.client_gstin_snapshot && <p>GSTIN: {invoice.client_gstin_snapshot}</p>}
          </div>
          <div>
            <h4>Dates</h4>
            <p>Issued: {invoice.issue_date}<br />Due: {invoice.due_date}</p>
            {invoice.business_gstin && <p>Seller GSTIN: {invoice.business_gstin}</p>}
          </div>
        </div>

        <div className="table-scroll">
          <table className="items-table">
            <thead>
              <tr><th>Description</th><th>HSN/SAC</th><th>Qty</th><th>Unit Price</th><th>Tax %</th><th>Amount</th></tr>
            </thead>
            <tbody>
              {invoice.items.map((item) => (
                <tr key={item.id}>
                  <td>{item.description}</td>
                  <td>{item.hsn_sac_code || "-"}</td>
                  <td>{item.quantity}</td>
                  <td>{money(item.unit_price, invoice.currency)}</td>
                  <td>{item.tax_rate_percent}%</td>
                  <td>{money(item.amount, invoice.currency)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="invoice-totals">
          <div><span>Subtotal</span><span>{money(invoice.subtotal, invoice.currency)}</span></div>
          {invoice.tax_type === "CGST_SGST" && (
            <>
              <div><span>CGST</span><span>{money(invoice.cgst_amount, invoice.currency)}</span></div>
              <div><span>SGST</span><span>{money(invoice.sgst_amount, invoice.currency)}</span></div>
            </>
          )}
          {invoice.tax_type === "IGST" && (
            <div><span>IGST</span><span>{money(invoice.igst_amount, invoice.currency)}</span></div>
          )}
          {invoice.tax_type === "EXPORT_ZERO_RATED" && (
            <div><span>GST</span><span>Zero-rated (export, LUT {invoice.lut_reference})</span></div>
          )}
          <div className="invoice-total-final"><span>Total</span><span>{money(invoice.total_amount, invoice.currency)}</span></div>
        </div>

        <div className="invoice-actions">
          {invoice.pdf_url && (
            <a className="btn btn-secondary" href={invoice.pdf_url} target="_blank" rel="noreferrer">Download PDF</a>
          )}
          {invoice.status === "paid" ? (
            <span className="badge badge-green badge-lg">Paid - thank you!</span>
          ) : invoice.payment_link_url ? (
            <a className="btn btn-primary" href={invoice.payment_link_url} target="_blank" rel="noreferrer">Pay Now</a>
          ) : (
            <span className="page-subtitle">A payment link hasn't been set up for this invoice yet.</span>
          )}
        </div>
      </div>

      <p className="public-page-brand">
        Invoiced with <a href="/">Freelancer Finance OS</a>
      </p>
    </div>
  );
}
