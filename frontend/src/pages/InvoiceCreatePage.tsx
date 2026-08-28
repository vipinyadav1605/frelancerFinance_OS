import { type FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createInvoice, getExchangeRate, listClients } from "../api/endpoints";
import { CURRENCIES } from "../constants";
import { useToast } from "../context/ToastContext";
import type { Client, Currency, InvoiceItemInput } from "../types";
import { extractErrorMessage } from "../utils/errors";
import { dateOrderError } from "../utils/validation";

function emptyItem(): InvoiceItemInput {
  return { description: "", hsn_sac_code: "", quantity: "1", unit_price: "0", tax_rate_percent: "18" };
}

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function addDaysISO(days: number) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

export function InvoiceCreatePage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [clients, setClients] = useState<Client[]>([]);
  const [clientId, setClientId] = useState<number | "">("");
  const [issueDate, setIssueDate] = useState(todayISO());
  const [dueDate, setDueDate] = useState(addDaysISO(14));
  const [currency, setCurrency] = useState<Currency>("INR");
  const [exchangeRate, setExchangeRate] = useState("1");
  const [fetchingRate, setFetchingRate] = useState(false);
  const [rateError, setRateError] = useState("");
  const [items, setItems] = useState<InvoiceItemInput[]>([emptyItem()]);
  const [clientError, setClientError] = useState("");
  const [dueDateError, setDueDateError] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => { listClients().then(setClients); }, []);

  useEffect(() => {
    if (currency === "INR") return;
    setFetchingRate(true);
    setRateError("");
    getExchangeRate(currency)
      .then(setExchangeRate)
      .catch(() => setRateError("Could not fetch a live rate - enter it manually."))
      .finally(() => setFetchingRate(false));
  }, [currency]);

  useEffect(() => {
    setDueDateError(dateOrderError(issueDate, dueDate, "Due date"));
  }, [issueDate, dueDate]);

  const selectedClient = clients.find((c) => c.id === clientId);

  function updateItem(index: number, key: keyof InvoiceItemInput, value: string) {
    setItems((prev) => prev.map((item, i) => (i === index ? { ...item, [key]: value } : item)));
  }

  function addItem() {
    setItems((prev) => [...prev, emptyItem()]);
  }

  function removeItem(index: number) {
    setItems((prev) => prev.filter((_, i) => i !== index));
  }

  const subtotal = items.reduce(
    (sum, item) => sum + (Number(item.quantity) || 0) * (Number(item.unit_price) || 0), 0
  );

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    const clientErr = clientId ? "" : "Please select a client.";
    const dueErr = dateOrderError(issueDate, dueDate, "Due date");
    setClientError(clientErr);
    setDueDateError(dueErr);
    if (clientErr || dueErr) return;

    setSubmitting(true);
    try {
      const invoice = await createInvoice({
        client: clientId as number,
        issue_date: issueDate,
        due_date: dueDate,
        currency,
        exchange_rate_to_inr: currency === "INR" ? "1" : exchangeRate,
        items,
      });
      toast.success(`Invoice ${invoice.invoice_number} created.`);
      navigate(`/invoices/${invoice.id}`);
    } catch (err) {
      setError(extractErrorMessage(err, "Could not create invoice."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>New Invoice</h1>
        <p className="page-subtitle">Tax treatment (CGST+SGST / IGST / export zero-rated) is calculated automatically (FR-4).</p>
      </div>

      <form className="card form" onSubmit={handleSubmit} noValidate>
        {error && <div className="alert alert-error">{error}</div>}

        <div className="form-row">
          <label>Client
            <select
              value={clientId} onChange={(e) => { setClientId(e.target.value ? Number(e.target.value) : ""); setClientError(""); }}
              className={clientError ? "field-error-input" : ""}
            >
              <option value="">Select a client</option>
              {clients.map((c) => <option key={c.id} value={c.id}>{c.name}{c.is_international ? " (international)" : ""}</option>)}
            </select>
            {clientError && <span className="field-error-text">{clientError}</span>}
          </label>
          <label>Currency
            <select value={currency} onChange={(e) => setCurrency(e.target.value as Currency)}>
              {CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </label>
        </div>

        {selectedClient?.is_international && (
          <div className="alert alert-info">
            This is an international client &mdash; this invoice will be treated as an export of
            services, zero-rated under LUT.
          </div>
        )}

        {currency !== "INR" && (
          <label>Exchange rate to INR (1 {currency} = ? INR)
            <input type="number" step="0.0001" value={exchangeRate} onChange={(e) => setExchangeRate(e.target.value)} required />
            {fetchingRate && <span className="field-hint-text">Fetching live rate...</span>}
            {rateError && <span className="field-error-text">{rateError}</span>}
          </label>
        )}

        <div className="form-row">
          <label>Issue date
            <input type="date" value={issueDate} onChange={(e) => setIssueDate(e.target.value)} required />
          </label>
          <label>Due date
            <input
              type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} required
              className={dueDateError ? "field-error-input" : ""}
            />
            {dueDateError && <span className="field-error-text">{dueDateError}</span>}
          </label>
        </div>

        <h3>Line Items</h3>
        <div className="table-scroll">
          <table className="items-table">
            <thead>
              <tr>
                <th>Description</th><th>HSN/SAC</th><th>Qty</th><th>Unit Price</th><th>Tax %</th><th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, i) => (
                <tr key={i}>
                  <td><input value={item.description} onChange={(e) => updateItem(i, "description", e.target.value)} required /></td>
                  <td><input value={item.hsn_sac_code} onChange={(e) => updateItem(i, "hsn_sac_code", e.target.value)} /></td>
                  <td><input type="number" step="0.01" min="0.01" value={item.quantity} onChange={(e) => updateItem(i, "quantity", e.target.value)} required /></td>
                  <td><input type="number" step="0.01" min="0" value={item.unit_price} onChange={(e) => updateItem(i, "unit_price", e.target.value)} required /></td>
                  <td><input type="number" step="0.01" min="0" value={item.tax_rate_percent} onChange={(e) => updateItem(i, "tax_rate_percent", e.target.value)} /></td>
                  <td>
                    {items.length > 1 && (
                      <button type="button" className="btn-link" onClick={() => removeItem(i)}>Remove</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <button type="button" className="btn btn-secondary" onClick={addItem}>+ Add Line Item</button>

        <div className="invoice-subtotal-preview">
          Subtotal (before tax): {currency} {subtotal.toFixed(2)}
        </div>

        <button className="btn btn-primary" type="submit" disabled={submitting}>
          {submitting && <span className="btn-spinner" />}
          {submitting ? "Creating..." : "Create Invoice"}
        </button>
      </form>
    </div>
  );
}
