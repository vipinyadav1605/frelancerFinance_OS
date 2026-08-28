import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listInvoices, markInvoicePaid } from "../api/endpoints";
import type { InvoiceListItem, InvoiceStatus } from "../types";

const MARKABLE_STATUSES: InvoiceStatus[] = ["sent", "overdue"];

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
  const [count, setCount] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [hasPrevious, setHasPrevious] = useState(false);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<InvoiceStatus | "">("");
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [bulkMarking, setBulkMarking] = useState(false);

  function load() {
    setLoading(true);
    listInvoices({ ...(status ? { status } : {}), page })
      .then((data) => {
        setInvoices(data.results);
        setCount(data.count);
        setHasNext(data.next !== null);
        setHasPrevious(data.previous !== null);
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    setSelected(new Set());
    load();
  }, [status, page]);

  function selectStatus(value: InvoiceStatus | "") {
    setStatus(value);
    setPage(1);
  }

  const markableSelected = invoices.filter(
    (inv) => selected.has(inv.id) && MARKABLE_STATUSES.includes(inv.status)
  );

  function toggleSelected(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  function toggleSelectAllMarkable() {
    const markableIds = invoices.filter((inv) => MARKABLE_STATUSES.includes(inv.status)).map((inv) => inv.id);
    const allSelected = markableIds.length > 0 && markableIds.every((id) => selected.has(id));
    setSelected(allSelected ? new Set() : new Set(markableIds));
  }

  async function handleBulkMarkPaid() {
    if (markableSelected.length === 0) return;
    if (!confirm(`Mark ${markableSelected.length} invoice(s) as paid in full, dated today?`)) return;
    setBulkMarking(true);
    const today = new Date().toISOString();
    try {
      await Promise.all(
        markableSelected.map((inv) => markInvoicePaid(inv.id, inv.total_amount, today))
      );
      setSelected(new Set());
      load();
    } finally {
      setBulkMarking(false);
    }
  }

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
            onClick={() => selectStatus(opt.value)}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {markableSelected.length > 0 && (
        <div className="bulk-toolbar">
          <span>{markableSelected.length} selected</span>
          <button className="btn btn-primary" onClick={handleBulkMarkPaid} disabled={bulkMarking}>
            {bulkMarking ? "Marking..." : "Mark Selected as Paid"}
          </button>
        </div>
      )}

      {loading ? (
        <div className="page-loading">Loading...</div>
      ) : invoices.length === 0 ? (
        <div className="empty-state">No invoices yet. Create your first invoice to get started.</div>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>
                <input
                  type="checkbox"
                  onChange={toggleSelectAllMarkable}
                  checked={invoices.some((inv) => MARKABLE_STATUSES.includes(inv.status)) &&
                    invoices.filter((inv) => MARKABLE_STATUSES.includes(inv.status)).every((inv) => selected.has(inv.id))}
                  title="Select all payable invoices"
                />
              </th>
              <th>Invoice #</th><th>Client</th><th>Issue Date</th><th>Due Date</th>
              <th>Amount</th><th>Status</th>
            </tr>
          </thead>
          <tbody>
            {invoices.map((inv) => (
              <tr key={inv.id}>
                <td>
                  {MARKABLE_STATUSES.includes(inv.status) && (
                    <input type="checkbox" checked={selected.has(inv.id)} onChange={() => toggleSelected(inv.id)} />
                  )}
                </td>
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

      {!loading && count > 0 && (
        <div className="filter-bar" style={{ justifyContent: "space-between", marginTop: "1rem" }}>
          <span className="page-subtitle">{count} invoice{count === 1 ? "" : "s"} total</span>
          <div className="form-actions">
            <button className="btn btn-secondary" disabled={!hasPrevious} onClick={() => setPage((p) => p - 1)}>Previous</button>
            <span className="page-subtitle" style={{ alignSelf: "center" }}>Page {page}</span>
            <button className="btn btn-secondary" disabled={!hasNext} onClick={() => setPage((p) => p + 1)}>Next</button>
          </div>
        </div>
      )}
    </div>
  );
}
