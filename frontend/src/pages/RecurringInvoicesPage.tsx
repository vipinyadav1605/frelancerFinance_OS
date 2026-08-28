import { type FormEvent, useEffect, useState } from "react";
import {
  createRecurringInvoiceProfile, deleteRecurringInvoiceProfile, listClients,
  listRecurringInvoiceProfiles, updateRecurringInvoiceProfile,
} from "../api/endpoints";
import { CURRENCIES } from "../constants";
import { useToast } from "../context/ToastContext";
import type { Client, Currency, RecurringFrequency, RecurringInvoiceItemInput, RecurringInvoiceProfile } from "../types";
import { extractErrorMessage } from "../utils/errors";
import { requiredError } from "../utils/validation";

function emptyItem(): RecurringInvoiceItemInput {
  return { description: "", hsn_sac_code: "", quantity: "1", unit_price: "0", tax_rate_percent: "18" };
}

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

const emptyForm = {
  client: "" as number | "",
  frequency: "monthly" as RecurringFrequency,
  currency: "INR" as Currency,
  exchange_rate_to_inr: "1",
  due_in_days: "14",
  next_run_date: todayISO(),
  is_active: true,
  auto_send: false,
  items: [emptyItem()],
};

function money(amount: string, currency: string) {
  return `${currency} ${Number(amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
}

export function RecurringInvoicesPage() {
  const toast = useToast();
  const [profiles, setProfiles] = useState<RecurringInvoiceProfile[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [clientError, setClientError] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  function load() {
    setLoading(true);
    listRecurringInvoiceProfiles().then(setProfiles).finally(() => setLoading(false));
  }

  useEffect(load, []);
  useEffect(() => { listClients().then(setClients); }, []);

  function update<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function updateItem(index: number, key: keyof RecurringInvoiceItemInput, value: string) {
    setForm((f) => ({
      ...f, items: f.items.map((item, i) => (i === index ? { ...item, [key]: value } : item)),
    }));
  }

  function addItem() {
    setForm((f) => ({ ...f, items: [...f.items, emptyItem()] }));
  }

  function removeItem(index: number) {
    setForm((f) => ({ ...f, items: f.items.filter((_, i) => i !== index) }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    const err = form.client ? "" : requiredError("", "Client");
    setClientError(err);
    if (err) return;

    setSaving(true);
    try {
      await createRecurringInvoiceProfile({
        client: form.client as number,
        frequency: form.frequency,
        currency: form.currency,
        exchange_rate_to_inr: form.currency === "INR" ? "1" : form.exchange_rate_to_inr,
        due_in_days: Number(form.due_in_days),
        next_run_date: form.next_run_date,
        is_active: form.is_active,
        auto_send: form.auto_send,
        items: form.items,
      });
      setForm(emptyForm);
      setShowForm(false);
      load();
      toast.success("Recurring invoice created.");
    } catch (err) {
      setError(extractErrorMessage(err, "Could not save recurring invoice."));
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive(profile: RecurringInvoiceProfile) {
    await updateRecurringInvoiceProfile(profile.id, { is_active: !profile.is_active });
    load();
    toast.success(profile.is_active ? "Recurring invoice paused." : "Recurring invoice resumed.");
  }

  async function handleDelete(profile: RecurringInvoiceProfile) {
    if (!confirm(`Stop and delete the recurring invoice for ${profile.client_name}?`)) return;
    await deleteRecurringInvoiceProfile(profile.id);
    load();
    toast.success("Recurring invoice deleted.");
  }

  return (
    <div className="page">
      <div className="page-header page-header-row">
        <div>
          <h1>Recurring Invoices</h1>
          <p className="page-subtitle">
            Set up a template once &mdash; a real invoice is generated automatically on each due date.
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm((v) => !v)}>+ New Recurring Invoice</button>
      </div>

      {showForm && (
        <form className="card form" onSubmit={handleSubmit} noValidate>
          {error && <div className="alert alert-error">{error}</div>}
          <div className="form-row">
            <label>Client
              <select
                value={form.client} onChange={(e) => { update("client", e.target.value ? Number(e.target.value) : ""); setClientError(""); }}
                className={clientError ? "field-error-input" : ""}
              >
                <option value="">Select a client</option>
                {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
              {clientError && <span className="field-error-text">{clientError}</span>}
            </label>
            <label>Frequency
              <select value={form.frequency} onChange={(e) => update("frequency", e.target.value as RecurringFrequency)}>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
              </select>
            </label>
          </div>
          <div className="form-row">
            <label>Currency
              <select value={form.currency} onChange={(e) => update("currency", e.target.value as Currency)}>
                {CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </label>
            {form.currency !== "INR" && (
              <label>Exchange rate to INR
                <input type="number" step="0.0001" value={form.exchange_rate_to_inr} onChange={(e) => update("exchange_rate_to_inr", e.target.value)} required />
              </label>
            )}
            <label>Due within (days)
              <input type="number" min={0} value={form.due_in_days} onChange={(e) => update("due_in_days", e.target.value)} required />
            </label>
          </div>
          <label>First invoice date
            <input type="date" value={form.next_run_date} onChange={(e) => update("next_run_date", e.target.value)} required />
          </label>
          <label className="checkbox-label">
            <input type="checkbox" checked={form.auto_send} onChange={(e) => update("auto_send", e.target.checked)} />
            Automatically email each generated invoice to the client
          </label>

          <h3>Line Items</h3>
          <div className="table-scroll">
            <table className="items-table">
              <thead>
                <tr><th>Description</th><th>HSN/SAC</th><th>Qty</th><th>Unit Price</th><th>Tax %</th><th></th></tr>
              </thead>
              <tbody>
                {form.items.map((item, i) => (
                  <tr key={i}>
                    <td><input value={item.description} onChange={(e) => updateItem(i, "description", e.target.value)} required /></td>
                    <td><input value={item.hsn_sac_code} onChange={(e) => updateItem(i, "hsn_sac_code", e.target.value)} /></td>
                    <td><input type="number" step="0.01" min="0.01" value={item.quantity} onChange={(e) => updateItem(i, "quantity", e.target.value)} required /></td>
                    <td><input type="number" step="0.01" min="0" value={item.unit_price} onChange={(e) => updateItem(i, "unit_price", e.target.value)} required /></td>
                    <td><input type="number" step="0.01" min="0" value={item.tax_rate_percent} onChange={(e) => updateItem(i, "tax_rate_percent", e.target.value)} /></td>
                    <td>{form.items.length > 1 && <button type="button" className="btn-link" onClick={() => removeItem(i)}>Remove</button>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button type="button" className="btn btn-secondary" onClick={addItem}>+ Add Line Item</button>

          <div className="form-actions">
            <button className="btn btn-primary" type="submit" disabled={saving}>
              {saving && <span className="btn-spinner" />}
              {saving ? "Saving..." : "Save Recurring Invoice"}
            </button>
            <button className="btn btn-secondary" type="button" onClick={() => setShowForm(false)}>Cancel</button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="page-loading"><span className="spinner-lg" /> Loading...</div>
      ) : profiles.length === 0 ? (
        <div className="empty-state">No recurring invoices yet. Set one up for a retainer or repeat client.</div>
      ) : (
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr><th>Client</th><th>Frequency</th><th>Next Invoice</th><th>Last Generated</th><th>Status</th><th></th></tr>
            </thead>
            <tbody>
              {profiles.map((p) => (
                <tr key={p.id}>
                  <td>{p.client_name}</td>
                  <td style={{ textTransform: "capitalize" }}>{p.frequency}</td>
                  <td>{p.next_run_date} <span style={{ color: "var(--grey)" }}>({money(p.items.reduce((s, i) => s + Number(i.quantity) * Number(i.unit_price), 0).toFixed(2), p.currency)})</span></td>
                  <td>{p.last_generated_invoice_number || "-"}</td>
                  <td>
                    <span className={`badge ${p.is_active ? "badge-green" : "badge-grey"}`}>{p.is_active ? "Active" : "Paused"}</span>
                  </td>
                  <td>
                    <button className="btn-link" onClick={() => toggleActive(p)}>{p.is_active ? "Pause" : "Resume"}</button>
                    {" "}&middot;{" "}
                    <button className="btn-link" onClick={() => handleDelete(p)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
