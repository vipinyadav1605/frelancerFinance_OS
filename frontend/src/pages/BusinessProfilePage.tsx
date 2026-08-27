import { type FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getBusinessProfile, saveBusinessProfile } from "../api/endpoints";
import { INDIAN_STATES } from "../constants";
import { useAuth } from "../context/AuthContext";
import { extractErrorMessage } from "../utils/errors";

const emptyForm = {
  business_name: "", pan: "", gstin: "", is_gst_registered: false,
  address: "", state: "", invoice_prefix: "INV", lut_reference: "",
};

export function BusinessProfilePage() {
  const { refreshUser } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState(emptyForm);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    getBusinessProfile()
      .then((profile) => { if (profile) setForm({ ...emptyForm, ...profile }); })
      .finally(() => setLoading(false));
  }, []);

  function update<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSaving(true);
    setSaved(false);
    try {
      await saveBusinessProfile(form);
      await refreshUser();
      setSaved(true);
    } catch (err) {
      setError(extractErrorMessage(err, "Could not save business profile."));
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="page-loading">Loading...</div>;

  return (
    <div className="page">
      <div className="page-header">
        <h1>Business Profile</h1>
        <p className="page-subtitle">These details appear on every invoice you send (FR-2).</p>
      </div>

      <form className="card form" onSubmit={handleSubmit}>
        {error && <div className="alert alert-error">{error}</div>}
        {saved && <div className="alert alert-success">Saved. <button type="button" className="btn-link" onClick={() => navigate("/invoices")}>Go to invoices &rarr;</button></div>}

        <label>Business name
          <input value={form.business_name} onChange={(e) => update("business_name", e.target.value)} required />
        </label>

        <div className="form-row">
          <label>PAN
            <input value={form.pan} onChange={(e) => update("pan", e.target.value.toUpperCase())} maxLength={10} />
          </label>
          <label>
            <span className="checkbox-label">
              <input type="checkbox" checked={form.is_gst_registered}
                     onChange={(e) => update("is_gst_registered", e.target.checked)} />
              I am GST-registered
            </span>
          </label>
        </div>

        {form.is_gst_registered && (
          <label>GSTIN
            <input value={form.gstin} onChange={(e) => update("gstin", e.target.value.toUpperCase())} maxLength={15} />
          </label>
        )}

        <label>Address
          <textarea value={form.address} onChange={(e) => update("address", e.target.value)} rows={2} />
        </label>

        <div className="form-row">
          <label>State
            <select value={form.state} onChange={(e) => update("state", e.target.value)} required>
              <option value="">Select state</option>
              {INDIAN_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>
          <label>Invoice number prefix
            <input value={form.invoice_prefix} onChange={(e) => update("invoice_prefix", e.target.value.toUpperCase())} maxLength={12} />
          </label>
        </div>

        <label>LUT reference (ARN)
          <input value={form.lut_reference} onChange={(e) => update("lut_reference", e.target.value)}
                 placeholder="Required only for export/international invoices" />
        </label>

        <button className="btn btn-primary" type="submit" disabled={saving}>
          {saving ? "Saving..." : "Save"}
        </button>
      </form>
    </div>
  );
}
