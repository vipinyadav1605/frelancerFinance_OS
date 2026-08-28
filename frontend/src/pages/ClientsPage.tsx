import { type FormEvent, useEffect, useState } from "react";
import { createClient, listClients, updateClient } from "../api/endpoints";
import { INDIAN_STATES } from "../constants";
import { useToast } from "../context/ToastContext";
import type { Client } from "../types";
import { extractErrorMessage } from "../utils/errors";
import { emailError, gstinError, requiredError } from "../utils/validation";

const emptyForm = {
  name: "", email: "", billing_address: "", country: "India", state: "", gstin: "",
};

const NO_ERRORS = { name: "", email: "", country: "", state: "", gstin: "" };

export function ClientsPage() {
  const toast = useToast();
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [fieldErrors, setFieldErrors] = useState(NO_ERRORS);
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
    setFieldErrors(NO_ERRORS);
    setEditingId(null);
    setError("");
    setShowForm(true);
  }

  function startEdit(client: Client) {
    setForm({
      name: client.name, email: client.email, billing_address: client.billing_address,
      country: client.country, state: client.state, gstin: client.gstin,
    });
    setFieldErrors(NO_ERRORS);
    setEditingId(client.id);
    setError("");
    setShowForm(true);
  }

  const isDomestic = form.country.trim().toLowerCase() === "india";

  function validate() {
    return {
      name: requiredError(form.name, "Name"),
      email: emailError(form.email, false),
      country: requiredError(form.country, "Country"),
      state: isDomestic ? requiredError(form.state, "State") : "",
      gstin: gstinError(form.gstin, false),
    };
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    const errors = validate();
    setFieldErrors(errors);
    if (Object.values(errors).some(Boolean)) return;

    setSaving(true);
    try {
      if (editingId) {
        await updateClient(editingId, form);
        toast.success("Client updated.");
      } else {
        await createClient(form);
        toast.success("Client added.");
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
        <form className="card form" onSubmit={handleSubmit} noValidate>
          {error && <div className="alert alert-error">{error}</div>}
          <label>Name
            <input
              value={form.name} onChange={(e) => update("name", e.target.value)}
              onBlur={() => setFieldErrors((f) => ({ ...f, name: requiredError(form.name, "Name") }))}
              className={fieldErrors.name ? "field-error-input" : ""}
            />
            {fieldErrors.name && <span className="field-error-text">{fieldErrors.name}</span>}
          </label>
          <div className="form-row">
            <label>Email
              <input
                type="email" value={form.email} onChange={(e) => update("email", e.target.value)}
                onBlur={() => setFieldErrors((f) => ({ ...f, email: emailError(form.email, false) }))}
                className={fieldErrors.email ? "field-error-input" : ""}
              />
              {fieldErrors.email && <span className="field-error-text">{fieldErrors.email}</span>}
            </label>
            <label>Country
              <input
                value={form.country} onChange={(e) => update("country", e.target.value)}
                onBlur={() => setFieldErrors((f) => ({ ...f, country: requiredError(form.country, "Country") }))}
                className={fieldErrors.country ? "field-error-input" : ""}
              />
              {fieldErrors.country && <span className="field-error-text">{fieldErrors.country}</span>}
            </label>
          </div>
          <label>Billing address
            <textarea value={form.billing_address} onChange={(e) => update("billing_address", e.target.value)} rows={2} />
          </label>
          {isDomestic && (
            <div className="form-row">
              <label>State
                <select
                  value={form.state} onChange={(e) => update("state", e.target.value)}
                  onBlur={() => setFieldErrors((f) => ({ ...f, state: requiredError(form.state, "State") }))}
                  className={fieldErrors.state ? "field-error-input" : ""}
                >
                  <option value="">Select state</option>
                  {INDIAN_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
                {fieldErrors.state && <span className="field-error-text">{fieldErrors.state}</span>}
              </label>
              <label>GSTIN (if registered)
                <input
                  value={form.gstin} onChange={(e) => update("gstin", e.target.value.toUpperCase())} maxLength={15}
                  onBlur={() => setFieldErrors((f) => ({ ...f, gstin: gstinError(form.gstin, false) }))}
                  className={fieldErrors.gstin ? "field-error-input" : ""}
                />
                {fieldErrors.gstin && <span className="field-error-text">{fieldErrors.gstin}</span>}
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
              {saving && <span className="btn-spinner" />}
              {saving ? "Saving..." : "Save Client"}
            </button>
            <button className="btn btn-secondary" type="button" onClick={() => setShowForm(false)}>Cancel</button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="page-loading"><span className="spinner-lg" /> Loading...</div>
      ) : clients.length === 0 ? (
        <div className="empty-state">No clients yet. Add your first client to get started.</div>
      ) : (
        <div className="table-scroll">
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
        </div>
      )}
    </div>
  );
}
