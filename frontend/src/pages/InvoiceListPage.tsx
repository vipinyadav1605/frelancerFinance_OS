import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listInvoices } from "../api/endpoints";
import type { InvoiceListItem, InvoiceStatus } from "../types";

const STATUS_OPTIONS: { value: InvoiceStatus | ""; label: string }[] = [
  { value: "", label: "All" },
  { value: "draft", label: "Draft" },
  { value: "sent", label: "Sent" },
  { value: "paid", label: "Paid" },
  { value: "overdue", label: "Overdue" },
];

const STATUS_BADGE: Record<InvoiceStatus, string> = {
  draft: "badge-grey", sent: "badge-blue", paid: "badge-green", overdue: "badge-red",
};

function currencyAmount(amount: string, currency: string) {
  const symbols: Record<string, string> = { INR: "₹", USD: "$", EUR: "€", GBP: "£" };
  return `${symbols[currency] ?? currency + " "}${Number(amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
}

export function InvoiceListPage() {
  const [invoices, setInvoices] = useState<InvoiceListItem[]>([]);
  const [status, setStatus] = useState<InvoiceStatus | "">("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    listInvoices(status ? { status } : {}).then(setInvoices).finally(() => setLoading(false));
  }, [status]);

  return (
    <div className="page">
      <div className="page-header page-header-row">
        <div>
          <h1>Invoices</h1>
          <p className="page-subtitle">Every invoice you've created, GST-compliant by default.</p>
        </div>
        <Link className="btn btn-primary" to="/invoices/new">+ New Invoice</Link>
      </div>

      <div className="filter-bar">
        {STATUS_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            className={`filter-chip ${status === opt.value ? "filter-chip-active" : ""}`}
            onClick={() => setStatus(opt.value)}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="page-loading">Loading...</div>
      ) : invoices.length === 0 ? (
        <div className="empty-state">No invoices yet. Create your first invoice to get started.</div>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Invoice #</th><th>Client</th><th>Issue Date</th><th>Due Date</th>
              <th>Amount</th><th>Status</th>
            </tr>
          </thead>
          <tbody>
            {invoices.map((inv) => (
              <tr key={inv.id}>
                <td><Link to={`/invoices/${inv.id}`}>{inv.invoice_number}</Link></td>
                <td>{inv.client_name}</td>
                <td>{inv.issue_date}</td>
                <td>{inv.due_date}</td>
                <td>{currencyAmount(inv.total_amount, inv.currency)}</td>
                <td><span className={`badge ${STATUS_BADGE[inv.status]}`}>{inv.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
