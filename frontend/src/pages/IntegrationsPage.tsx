import { type FormEvent, useEffect, useState } from "react";
import {
  createApiKey, createWebhookSubscription, deleteWebhookSubscription, listApiKeys,
  listWebhookSubscriptions, revokeApiKey, updateWebhookSubscription,
} from "../api/endpoints";
import { useToast } from "../context/ToastContext";
import type { ApiKey, ApiKeyCreated, WebhookEvent, WebhookSubscription } from "../types";
import { extractErrorMessage } from "../utils/errors";
import { requiredError } from "../utils/validation";

const WEBHOOK_EVENTS: WebhookEvent[] = ["invoice.paid", "invoice.overdue", "expense.created"];

function urlError(value: string): string {
  if (!value.trim()) return "URL is required.";
  try {
    const parsed = new URL(value.trim());
    return ["http:", "https:"].includes(parsed.protocol) ? "" : "URL must start with http:// or https://.";
  } catch {
    return "Enter a valid URL (e.g. https://example.com/hook).";
  }
}

export function IntegrationsPage() {
  const toast = useToast();
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [newKeyName, setNewKeyName] = useState("");
  const [keyNameError, setKeyNameError] = useState("");
  const [justCreatedKey, setJustCreatedKey] = useState<ApiKeyCreated | null>(null);
  const [keyError, setKeyError] = useState("");
  const [creatingKey, setCreatingKey] = useState(false);

  const [webhooks, setWebhooks] = useState<WebhookSubscription[]>([]);
  const [newWebhookUrl, setNewWebhookUrl] = useState("");
  const [webhookUrlError, setWebhookUrlError] = useState("");
  const [newWebhookEvent, setNewWebhookEvent] = useState<WebhookEvent>("invoice.paid");
  const [webhookError, setWebhookError] = useState("");
  const [creatingWebhook, setCreatingWebhook] = useState(false);

  function loadApiKeys() {
    listApiKeys().then(setApiKeys);
  }
  function loadWebhooks() {
    listWebhookSubscriptions().then(setWebhooks);
  }

  useEffect(loadApiKeys, []);
  useEffect(loadWebhooks, []);

  async function handleCreateKey(e: FormEvent) {
    e.preventDefault();
    setKeyError("");
    const err = requiredError(newKeyName, "Name");
    setKeyNameError(err);
    if (err) return;

    setCreatingKey(true);
    try {
      const created = await createApiKey(newKeyName.trim());
      setJustCreatedKey(created);
      setNewKeyName("");
      loadApiKeys();
      toast.success("API key created.");
    } catch (err) {
      setKeyError(extractErrorMessage(err, "Could not create API key."));
    } finally {
      setCreatingKey(false);
    }
  }

  async function handleRevokeKey(id: number) {
    if (!confirm("Revoke this API key? Any script using it will stop working immediately.")) return;
    await revokeApiKey(id);
    loadApiKeys();
    toast.success("API key revoked.");
  }

  async function handleCreateWebhook(e: FormEvent) {
    e.preventDefault();
    setWebhookError("");
    const err = urlError(newWebhookUrl);
    setWebhookUrlError(err);
    if (err) return;

    setCreatingWebhook(true);
    try {
      await createWebhookSubscription(newWebhookUrl.trim(), newWebhookEvent);
      setNewWebhookUrl("");
      loadWebhooks();
      toast.success("Webhook added.");
    } catch (err) {
      setWebhookError(extractErrorMessage(err, "Could not create webhook."));
    } finally {
      setCreatingWebhook(false);
    }
  }

  async function toggleWebhookActive(webhook: WebhookSubscription) {
    await updateWebhookSubscription(webhook.id, !webhook.is_active);
    loadWebhooks();
    toast.success(webhook.is_active ? "Webhook paused." : "Webhook resumed.");
  }

  async function handleDeleteWebhook(id: number) {
    if (!confirm("Delete this webhook subscription?")) return;
    await deleteWebhookSubscription(id);
    loadWebhooks();
    toast.success("Webhook deleted.");
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Integrations</h1>
        <p className="page-subtitle">API keys for your own scripts, and webhooks for third-party automation.</p>
      </div>

      <div className="card">
        <h3>API Keys</h3>
        <p className="page-subtitle">
          Use an API key instead of logging in from a script or automation tool. Send it as{" "}
          <code>Authorization: Api-Key &lt;key&gt;</code>.
        </p>

        {justCreatedKey && (
          <div className="alert alert-success">
            Your new key (copy it now &mdash; it won't be shown again): <br />
            <code style={{ userSelect: "all", wordBreak: "break-all" }}>{justCreatedKey.key}</code>
          </div>
        )}

        <form className="form-inline" onSubmit={handleCreateKey} noValidate>
          {keyError && <div className="alert alert-error">{keyError}</div>}
          <label style={{ flex: 1 }}>Name
            <input
              value={newKeyName} onChange={(e) => setNewKeyName(e.target.value)} placeholder="e.g. My Zapier flow"
              onBlur={() => setKeyNameError(requiredError(newKeyName, "Name"))}
              className={keyNameError ? "field-error-input" : ""}
            />
            {keyNameError && <span className="field-error-text">{keyNameError}</span>}
          </label>
          <button className="btn btn-primary" type="submit" disabled={creatingKey}>
            {creatingKey && <span className="btn-spinner" />}
            {creatingKey ? "Generating..." : "Generate Key"}
          </button>
        </form>

        {apiKeys.length > 0 && (
          <div className="table-scroll" style={{ marginTop: "1rem" }}>
            <table className="data-table">
              <thead><tr><th>Name</th><th>Prefix</th><th>Last Used</th><th>Status</th><th></th></tr></thead>
              <tbody>
                {apiKeys.map((k) => (
                  <tr key={k.id}>
                    <td>{k.name}</td>
                    <td><code>{k.display_prefix}...</code></td>
                    <td>{k.last_used_at ? new Date(k.last_used_at).toLocaleString() : "Never"}</td>
                    <td><span className={`badge ${k.is_active ? "badge-green" : "badge-grey"}`}>{k.is_active ? "Active" : "Revoked"}</span></td>
                    <td>{k.is_active && <button className="btn-link" onClick={() => handleRevokeKey(k.id)}>Revoke</button>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card">
        <h3>Webhooks</h3>
        <p className="page-subtitle">
          Get an HTTP POST when something happens &mdash; e.g. notify a Slack channel via a webhook
          relay when an invoice is paid. Each request is signed with the subscription's secret in the{" "}
          <code>X-Ffos-Signature</code> header (HMAC-SHA256 of the raw body).
        </p>

        <form className="form-row" onSubmit={handleCreateWebhook} noValidate>
          {webhookError && <div className="alert alert-error">{webhookError}</div>}
          <label style={{ flex: 2 }}>URL
            <input
              type="url" value={newWebhookUrl} onChange={(e) => setNewWebhookUrl(e.target.value)} placeholder="https://..."
              onBlur={() => setWebhookUrlError(urlError(newWebhookUrl))}
              className={webhookUrlError ? "field-error-input" : ""}
            />
            {webhookUrlError && <span className="field-error-text">{webhookUrlError}</span>}
          </label>
          <label>Event
            <select value={newWebhookEvent} onChange={(e) => setNewWebhookEvent(e.target.value as WebhookEvent)}>
              {WEBHOOK_EVENTS.map((ev) => <option key={ev} value={ev}>{ev}</option>)}
            </select>
          </label>
          <label style={{ flex: "0 0 auto", justifyContent: "flex-end" }}>
            <span style={{ opacity: 0 }}>.</span>
            <button className="btn btn-primary" type="submit" disabled={creatingWebhook}>
              {creatingWebhook && <span className="btn-spinner" />}
              {creatingWebhook ? "Adding..." : "Add Webhook"}
            </button>
          </label>
        </form>

        {webhooks.length === 0 ? (
          <div className="empty-state" style={{ marginTop: "1rem" }}>No webhooks configured yet.</div>
        ) : (
          <div style={{ marginTop: "1rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
            {webhooks.map((w) => (
              <div key={w.id} className="card" style={{ margin: 0, background: "var(--bg)" }}>
                <div className="page-header-row">
                  <div>
                    <strong>{w.event}</strong> &rarr; {w.url}
                    <div className="page-subtitle">Secret: <code>{w.secret}</code></div>
                  </div>
                  <div className="form-actions">
                    <span className={`badge ${w.is_active ? "badge-green" : "badge-grey"}`}>{w.is_active ? "Active" : "Paused"}</span>
                    <button className="btn-link" onClick={() => toggleWebhookActive(w)}>{w.is_active ? "Pause" : "Resume"}</button>
                    <button className="btn-link" onClick={() => handleDeleteWebhook(w.id)}>Delete</button>
                  </div>
                </div>
                {w.recent_deliveries.length > 0 && (
                  <div className="table-scroll" style={{ marginTop: "0.6rem" }}>
                    <table className="data-table">
                      <thead><tr><th>When</th><th>Status</th><th>Result</th></tr></thead>
                      <tbody>
                        {w.recent_deliveries.map((d) => (
                          <tr key={d.id}>
                            <td>{new Date(d.created_at).toLocaleString()}</td>
                            <td>{d.status_code ?? "-"}</td>
                            <td>
                              <span className={`badge ${d.success ? "badge-green" : "badge-red"}`}>{d.success ? "Delivered" : "Failed"}</span>
                              {!d.success && d.error_message && <span className="page-subtitle"> {d.error_message}</span>}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
