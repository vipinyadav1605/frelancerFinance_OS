import { type FormEvent, useEffect, useState } from "react";
import { createClient, listClients, updateClient } from "../api/endpoints";
import { INDIAN_STATES } from "../constants";
import type { Client } from "../types";
import { extractErrorMessage } from "../utils/errors";

const emptyForm = {
  name: "", email: "", billing_address: "", country: "India", state: "", gstin: "",
};

export function ClientsPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  function load() {
    setLoading(true);
    listClients().then(setClients).finally(() => setLoading(false));
  }

  useEffect(load, []);

  function update<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function startAdd() {
    setForm(emptyForm);
    setEditingId(null);
    setError("");
    setShowForm(true);
  }

  function startEdit(client: Client) {
    setForm({
      name: client.name, email: client.email, billing_address: client.billing_address,
      country: client.country, state: client.state, gstin: client.gstin,
    });
    setEditingId(client.id);
    setError("");
    setShowForm(true);
  }

  const isDomestic = form.country.trim().toLowerCase() === "india";

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      if (editingId) {
        await updateClient(editingId, form);
      } else {
        await createClient(form);
      }
      setShowForm(false);
      load();
    } catch (err) {
      setError(extractErrorMessage(err, "Could not save client."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page">
      <div className="page-header page-header-row">
        <div>
          <h1>Clients</h1>
          <p className="page-subtitle">Manage the clients you bill (FR-3).</p>
        </div>
        <button className="btn btn-primary" onClick={startAdd}>+ Add Client</button>
      </div>

      {showForm && (
        <form className="card form" onSubmit={handleSubmit}>
          {error && <div className="alert alert-error">{error}</div>}
          <label>Name
            <input value={form.name} onChange={(e) => update("name", e.target.value)} required />
          </label>
          <div className="form-row">
            <label>Email
              <input type="email" value={form.email} onChange={(e) => update("email", e.target.value)} />
            </label>
            <label>Country
              <input value={form.country} onChange={(e) => update("country", e.target.value)} required />
            </label>
          </div>
          <label>Billing address
            <textarea value={form.billing_address} onChange={(e) => update("billing_address", e.target.value)} rows={2} />
          </label>
          {isDomestic && (
            <div className="form-row">
              <label>State
                <select value={form.state} onChange={(e) => update("state", e.target.value)} required={isDomestic}>
                  <option value="">Select state</option>
                  {INDIAN_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </label>
              <label>GSTIN (if registered)
                <input value={form.gstin} onChange={(e) => update("gstin", e.target.value.toUpperCase())} maxLength={15} />
              </label>
            </div>
          )}
          {!isDomestic && (
            <div className="alert alert-info">
              This client will be marked international &mdash; invoices to them will be treated as
              zero-rated exports under LUT (FR-4).
            </div>
          )}
          <div className="form-actions">
            <button className="btn btn-primary" type="submit" disabled={saving}>
              {saving ? "Saving..." : "Save Client"}
            </button>
            <button className="btn btn-secondary" type="button" onClick={() => setShowForm(false)}>Cancel</button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="page-loading">Loading...</div>
      ) : clients.length === 0 ? (
        <div className="empty-state">No clients yet. Add your first client to get started.</div>
      ) : (
        <table className="data-table">
          <thead>
            <tr><th>Name</th><th>Email</th><th>Country</th><th>Type</th><th></th></tr>
          </thead>
          <tbody>
            {clients.map((c) => (
              <tr key={c.id}>
                <td>{c.name}</td>
                <td>{c.email || "-"}</td>
                <td>{c.country}</td>
                <td>{c.is_international ? <span className="badge badge-amber">International</span> : <span className="badge badge-blue">Domestic</span>}</td>
                <td><button className="btn-link" onClick={() => startEdit(c)}>Edit</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
