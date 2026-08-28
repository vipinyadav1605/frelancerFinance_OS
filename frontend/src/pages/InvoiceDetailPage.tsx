import { type FormEvent, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getInvoice, markInvoicePaid, sendInvoice } from "../api/endpoints";
import type { InvoiceDetail } from "../types";
import { extractErrorMessage } from "../utils/errors";

const TAX_TYPE_LABEL: Record<string, string> = {
  CGST_SGST: "CGST + SGST (same state)",
  IGST: "IGST (other state)",
  EXPORT_ZERO_RATED: "Export of services (zero-rated, LUT)",
};

const CURRENCY_SYMBOLS: Record<string, string> = { INR: "₹", USD: "$", EUR: "€", GBP: "£" };

function money(amount: string, currency: string) {
  return `${CURRENCY_SYMBOLS[currency] ?? currency + " "}${Number(amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
}

export function InvoiceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [invoice, setInvoice] = useState<InvoiceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionError, setActionError] = useState("");
  const [sending, setSending] = useState(false);
  const [showMarkPaid, setShowMarkPaid] = useState(false);
  const [paidAmount, setPaidAmount] = useState("");
  const [paidDate, setPaidDate] = useState(new Date().toISOString().slice(0, 16));
  const [marking, setMarking] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);

  function load() {
    if (!id) return;
    setLoading(true);
    getInvoice(Number(id)).then((inv) => {
      setInvoice(inv);
      setPaidAmount(inv.total_amount);
    }).finally(() => setLoading(false));
  }

  useEffect(load, [id]);

  async function handleSend() {
    if (!invoice) return;
    setActionError("");
    setSending(true);
    try {
      const updated = await sendInvoice(invoice.id);
      setInvoice(updated);
    } catch (err) {
      setActionError(extractErrorMessage(err, "Could not send invoice."));
    } finally {
      setSending(false);
    }
  }

  async function handleMarkPaid(e: FormEvent) {
    e.preventDefault();
    if (!invoice) return;
    setActionError("");
    setMarking(true);
    try {
      const updated = await markInvoicePaid(invoice.id, paidAmount, new Date(paidDate).toISOString());
      setInvoice(updated);
      setShowMarkPaid(false);
    } catch (err) {
      setActionError(extractErrorMessage(err, "Could not record payment."));
    } finally {
      setMarking(false);
    }
  }

  async function handleCopyClientLink() {
    if (!invoice) return;
    const url = `${window.location.origin}/pay/${invoice.public_view_token}`;
    try {
      await navigator.clipboard.writeText(url);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
    } catch {
      // Clipboard API can fail (e.g. insecure context) - nothing more we can do here.
    }
  }

  if (loading) return <div className="page-loading">Loading...</div>;
  if (!invoice) return <div className="page">Invoice not found.</div>;

  return (
    <div className="page">
      <div className="page-header page-header-row">
        <div>
          <h1>{invoice.invoice_number}</h1>
          <p className="page-subtitle">{invoice.client_name_snapshot} &bull; {TAX_TYPE_LABEL[invoice.tax_type]}</p>
        </div>
        <span className={`badge badge-lg badge-${invoice.status === "paid" ? "green" : invoice.status === "overdue" ? "red" : invoice.status === "sent" ? "blue" : "grey"}`}>
          {invoice.status}
        </span>
      </div>

      {actionError && <div className="alert alert-error">{actionError}</div>}

      <div className="card">
        <div className="invoice-detail-grid">
          <div>
            <h4>Bill To</h4>
            <p>{invoice.client_name_snapshot}<br />{invoice.client_address_snapshot}<br />{invoice.client_country_snapshot}</p>
            {invoice.client_gstin_snapshot && <p>GSTIN: {invoice.client_gstin_snapshot}</p>}
          </div>
          <div>
            <h4>Dates</h4>
            <p>Issued: {invoice.issue_date}<br />Due: {invoice.due_date}</p>
          </div>
        </div>

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
          <div className="invoice-total-final"><span>Total</span><span>{money(invoice.total_amount, invoice.currency)}</span></div>
        </div>

        <div className="invoice-actions">
          {invoice.pdf_url && (
            <a className="btn btn-secondary" href={invoice.pdf_url} target="_blank" rel="noreferrer">Download PDF</a>
          )}
          {invoice.status === "draft" && (
            <button className="btn btn-primary" onClick={handleSend} disabled={sending}>
              {sending ? "Sending..." : "Send to Client"}
            </button>
          )}
          {invoice.status !== "paid" && (
            <button className="btn btn-secondary" onClick={() => setShowMarkPaid((v) => !v)}>Mark as Paid</button>
          )}
          {invoice.payment_link_url && (
            <a className="btn-link" href={invoice.payment_link_url} target="_blank" rel="noreferrer">View payment link</a>
          )}
          <button className="btn-link" onClick={handleCopyClientLink}>
            {copiedLink ? "Copied!" : "Copy client view link"}
          </button>
        </div>

        {showMarkPaid && (
          <form className="form form-inline" onSubmit={handleMarkPaid}>
            <label>Amount received
              <input type="number" step="0.01" value={paidAmount} onChange={(e) => setPaidAmount(e.target.value)} required />
            </label>
            <label>Payment date
              <input type="datetime-local" value={paidDate} onChange={(e) => setPaidDate(e.target.value)} required />
            </label>
            <button className="btn btn-primary" type="submit" disabled={marking}>
              {marking ? "Saving..." : "Confirm Payment"}
            </button>
          </form>
        )}
      </div>

      {invoice.payments.length > 0 && (
        <div className="card">
          <h4>Payment History</h4>
          <table className="data-table">
            <thead><tr><th>Date</th><th>Amount</th><th>Method</th><th>Status</th></tr></thead>
            <tbody>
              {invoice.payments.map((p) => (
                <tr key={p.id}>
                  <td>{new Date(p.payment_date).toLocaleString()}</td>
                  <td>{money(p.amount, invoice.currency)}</td>
                  <td>{p.method}</td>
                  <td>{p.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
