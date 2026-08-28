import { type FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getBusinessProfile, saveBusinessProfile } from "../api/endpoints";
import { INDIAN_STATES } from "../constants";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { extractErrorMessage } from "../utils/errors";
import { gstinError, panError, requiredError } from "../utils/validation";

const emptyForm = {
  business_name: "", pan: "", gstin: "", is_gst_registered: false,
  address: "", state: "", invoice_prefix: "INV", lut_reference: "", email_signoff: "",
};

const NO_ERRORS = { business_name: "", pan: "", gstin: "", state: "" };

export function BusinessProfilePage() {
  const { refreshUser } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [form, setForm] = useState(emptyForm);
  const [fieldErrors, setFieldErrors] = useState(NO_ERRORS);
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

  function validate() {
    return {
      business_name: requiredError(form.business_name, "Business name"),
      pan: panError(form.pan),
      gstin: form.is_gst_registered ? gstinError(form.gstin, true) : "",
      state: requiredError(form.state, "State"),
    };
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSaved(false);
    const errors = validate();
    setFieldErrors(errors);
    if (Object.values(errors).some(Boolean)) return;

    setSaving(true);
    try {
      await saveBusinessProfile(form);
      await refreshUser();
      setSaved(true);
      toast.success("Business profile saved.");
    } catch (err) {
      setError(extractErrorMessage(err, "Could not save business profile."));
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="page-loading"><span className="spinner-lg" /> Loading...</div>;

  return (
    <div className="page">
      <div className="page-header">
        <h1>Business Profile</h1>
        <p className="page-subtitle">These details appear on every invoice you send (FR-2).</p>
      </div>

      <form className="card form" onSubmit={handleSubmit} noValidate>
        {error && <div className="alert alert-error">{error}</div>}
        {saved && <div className="alert alert-success">Saved. <button type="button" className="btn-link" onClick={() => navigate("/invoices")}>Go to invoices &rarr;</button></div>}

        <label>Business name
          <input
            value={form.business_name} onChange={(e) => update("business_name", e.target.value)}
            onBlur={() => setFieldErrors((f) => ({ ...f, business_name: requiredError(form.business_name, "Business name") }))}
            className={fieldErrors.business_name ? "field-error-input" : ""}
          />
          {fieldErrors.business_name && <span className="field-error-text">{fieldErrors.business_name}</span>}
        </label>

        <div className="form-row">
          <label>PAN
            <input
              value={form.pan} onChange={(e) => update("pan", e.target.value.toUpperCase())} maxLength={10}
              onBlur={() => setFieldErrors((f) => ({ ...f, pan: panError(form.pan) }))}
              className={fieldErrors.pan ? "field-error-input" : ""}
            />
            {fieldErrors.pan && <span className="field-error-text">{fieldErrors.pan}</span>}
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
            <input
              value={form.gstin} onChange={(e) => update("gstin", e.target.value.toUpperCase())} maxLength={15}
              onBlur={() => setFieldErrors((f) => ({ ...f, gstin: gstinError(form.gstin, true) }))}
              className={fieldErrors.gstin ? "field-error-input" : ""}
            />
            {fieldErrors.gstin && <span className="field-error-text">{fieldErrors.gstin}</span>}
          </label>
        )}

        <label>Address
          <textarea value={form.address} onChange={(e) => update("address", e.target.value)} rows={2} />
        </label>

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
          <label>Invoice number prefix
            <input value={form.invoice_prefix} onChange={(e) => update("invoice_prefix", e.target.value.toUpperCase())} maxLength={12} />
          </label>
        </div>

        <label>LUT reference (ARN)
          <input value={form.lut_reference} onChange={(e) => update("lut_reference", e.target.value)}
                 placeholder="Required only for export/international invoices" />
        </label>

        <label>Invoice email sign-off (optional)
          <textarea value={form.email_signoff} onChange={(e) => update("email_signoff", e.target.value)} rows={2}
                    placeholder={`Defaults to "Thanks,\\n${form.business_name || "Your Business Name"}"`} />
        </label>

        <button className="btn btn-primary" type="submit" disabled={saving}>
          {saving && <span className="btn-spinner" />}
          {saving ? "Saving..." : "Save"}
        </button>
      </form>
    </div>
  );
}
