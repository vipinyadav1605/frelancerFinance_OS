import { type FormEvent, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  changeEmail, changePassword, deleteAccount, downloadDataExport, getNotificationPreference,
  updateNotificationPreference,
} from "../api/endpoints";
import { useAuth } from "../context/AuthContext";
import type { NotificationPreference } from "../types";
import { applyTheme, getStoredTheme, type Theme } from "../utils/theme";
import { extractErrorMessage } from "../utils/errors";
import { BusinessProfilePage } from "./BusinessProfilePage";
import { IntegrationsPage } from "./IntegrationsPage";

type Tab = "profile" | "business" | "security" | "notifications" | "integrations" | "danger";

const TABS: { key: Tab; label: string }[] = [
  { key: "profile", label: "Profile" },
  { key: "business", label: "Business" },
  { key: "security", label: "Security" },
  { key: "notifications", label: "Notifications" },
  { key: "integrations", label: "Integrations" },
  { key: "danger", label: "Danger Zone" },
];

function ToggleSwitch({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="toggle-switch">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span className="toggle-switch-track" />
    </label>
  );
}

function ProfileTab() {
  const { user } = useAuth();
  const [theme, setTheme] = useState<Theme>(getStoredTheme());

  function toggleTheme(dark: boolean) {
    const next: Theme = dark ? "dark" : "light";
    setTheme(next);
    applyTheme(next);
  }

  return (
    <div className="card">
      <h3>Profile</h3>
      <p className="page-subtitle">Name: {user?.name || "-"}</p>
      <p className="page-subtitle">Email: {user?.email}</p>
      <div className="toggle-row" style={{ marginTop: "0.8rem" }}>
        <div>
          <div className="toggle-row-label">Dark mode</div>
          <div className="toggle-row-hint">Applies immediately, remembered on this device.</div>
        </div>
        <ToggleSwitch checked={theme === "dark"} onChange={toggleTheme} />
      </div>
    </div>
  );
}

function SecurityTab() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [passwordSaved, setPasswordSaved] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);

  const [newEmail, setNewEmail] = useState(user?.email ?? "");
  const [emailPassword, setEmailPassword] = useState("");
  const [emailError, setEmailError] = useState("");
  const [emailSaved, setEmailSaved] = useState(false);
  const [savingEmail, setSavingEmail] = useState(false);

  async function handlePasswordSubmit(e: FormEvent) {
    e.preventDefault();
    setPasswordError("");
    setPasswordSaved(false);
    setSavingPassword(true);
    try {
      await changePassword(currentPassword, newPassword);
      setPasswordSaved(true);
      setCurrentPassword("");
      setNewPassword("");
    } catch (err) {
      setPasswordError(extractErrorMessage(err, "Could not change password."));
    } finally {
      setSavingPassword(false);
    }
  }

  async function handleEmailSubmit(e: FormEvent) {
    e.preventDefault();
    setEmailError("");
    setEmailSaved(false);
    setSavingEmail(true);
    try {
      await changeEmail(newEmail, emailPassword);
      setEmailSaved(true);
      setEmailPassword("");
    } catch (err) {
      setEmailError(extractErrorMessage(err, "Could not change email."));
    } finally {
      setSavingEmail(false);
    }
  }

  async function handleLogoutEverywhere() {
    if (!confirm("Log out of this device now?")) return;
    await logout();
    navigate("/login");
  }

  return (
    <>
      <form className="card form" onSubmit={handlePasswordSubmit}>
        <h3>Change Password</h3>
        {passwordError && <div className="alert alert-error">{passwordError}</div>}
        {passwordSaved && <div className="alert alert-success">Password changed.</div>}
        <label>Current password
          <input type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} required />
        </label>
        <label>New password
          <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required minLength={8} />
        </label>
        <button className="btn btn-primary" type="submit" disabled={savingPassword}>
          {savingPassword ? "Saving..." : "Change Password"}
        </button>
      </form>

      <form className="card form" onSubmit={handleEmailSubmit}>
        <h3>Change Email</h3>
        {emailError && <div className="alert alert-error">{emailError}</div>}
        {emailSaved && <div className="alert alert-success">Email changed. Use your new email to log in next time.</div>}
        <label>New email
          <input type="email" value={newEmail} onChange={(e) => setNewEmail(e.target.value)} required />
        </label>
        <label>Current password (to confirm)
          <input type="password" value={emailPassword} onChange={(e) => setEmailPassword(e.target.value)} required />
        </label>
        <button className="btn btn-primary" type="submit" disabled={savingEmail}>
          {savingEmail ? "Saving..." : "Change Email"}
        </button>
      </form>

      <div className="card">
        <h3>Sessions</h3>
        <p className="page-subtitle">Log out of your account on this device.</p>
        <button className="btn btn-secondary" onClick={handleLogoutEverywhere}>Log Out</button>
      </div>
    </>
  );
}

function NotificationsTab() {
  const [prefs, setPrefs] = useState<NotificationPreference | null>(null);
  const [error, setError] = useState("");

  useEffect(() => { getNotificationPreference().then(setPrefs); }, []);

  async function update(key: keyof NotificationPreference, value: boolean) {
    if (!prefs) return;
    const next = { ...prefs, [key]: value };
    setPrefs(next);
    try {
      await updateNotificationPreference(next);
    } catch (err) {
      setError(extractErrorMessage(err, "Could not save preference."));
      setPrefs(prefs); // revert on failure
    }
  }

  if (!prefs) return <div className="card"><div className="page-loading">Loading...</div></div>;

  return (
    <div className="card">
      <h3>Email Notifications</h3>
      <p className="page-subtitle">In-app notifications (the bell icon) always fire regardless of these settings.</p>
      {error && <div className="alert alert-error">{error}</div>}
      <div className="toggle-row">
        <div>
          <div className="toggle-row-label">Payment received</div>
          <div className="toggle-row-hint">Email me when an invoice is marked paid.</div>
        </div>
        <ToggleSwitch checked={prefs.payment_confirmation_emails} onChange={(v) => update("payment_confirmation_emails", v)} />
      </div>
      <div className="toggle-row">
        <div>
          <div className="toggle-row-label">Webhook delivery failures</div>
          <div className="toggle-row-hint">Email me when an outgoing webhook fails to deliver.</div>
        </div>
        <ToggleSwitch checked={prefs.webhook_failure_emails} onChange={(v) => update("webhook_failure_emails", v)} />
      </div>
    </div>
  );
}

function DangerZoneTab() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [exporting, setExporting] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const [deleteError, setDeleteError] = useState("");
  const [deleting, setDeleting] = useState(false);

  async function handleExport() {
    setExporting(true);
    try {
      await downloadDataExport();
    } finally {
      setExporting(false);
    }
  }

  async function handleDelete(e: FormEvent) {
    e.preventDefault();
    setDeleteError("");
    if (!confirm("This permanently deletes your account and all data. This cannot be undone. Continue?")) return;
    setDeleting(true);
    try {
      await deleteAccount(deletePassword);
      await logout();
      navigate("/login");
    } catch (err) {
      setDeleteError(extractErrorMessage(err, "Could not delete account."));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <>
      <div className="card">
        <h3>Export Your Data</h3>
        <p className="page-subtitle">Download all your clients, invoices, and expenses as a zip of CSV files.</p>
        <button className="btn btn-secondary" onClick={handleExport} disabled={exporting}>
          {exporting ? "Preparing..." : "Download All My Data"}
        </button>
      </div>

      <form className="card form danger-zone" onSubmit={handleDelete}>
        <h3>Delete Account</h3>
        <p className="page-subtitle">
          Permanently deletes your account, business profile, clients, invoices, expenses, and
          everything else. This cannot be undone.
        </p>
        {deleteError && <div className="alert alert-error">{deleteError}</div>}
        <label>Current password (to confirm)
          <input type="password" value={deletePassword} onChange={(e) => setDeletePassword(e.target.value)} required />
        </label>
        <button className="btn btn-primary" type="submit" style={{ background: "var(--red)" }} disabled={deleting}>
          {deleting ? "Deleting..." : "Permanently Delete My Account"}
        </button>
      </form>
    </>
  );
}

const TAB_KEYS = TABS.map((t) => t.key);

function isTab(value: string | null): value is Tab {
  return value !== null && (TAB_KEYS as string[]).includes(value);
}

export function SettingsPage() {
  const [searchParams] = useSearchParams();
  const requestedTab = searchParams.get("tab");
  const [tab, setTab] = useState<Tab>(isTab(requestedTab) ? requestedTab : "profile");

  return (
    <div className="page">
      <div className="page-header">
        <h1>Settings</h1>
        <p className="page-subtitle">Manage your profile, business details, security, and integrations.</p>
      </div>

      <div className="settings-layout">
        <div className="settings-tabs">
          {TABS.map((t) => (
            <button
              key={t.key}
              className={`settings-tab ${tab === t.key ? "settings-tab-active" : ""}`}
              onClick={() => setTab(t.key)}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="settings-content">
          {tab === "profile" && <ProfileTab />}
          {tab === "business" && <BusinessProfilePage />}
          {tab === "security" && <SecurityTab />}
          {tab === "notifications" && <NotificationsTab />}
          {tab === "integrations" && <IntegrationsPage />}
          {tab === "danger" && <DangerZoneTab />}
        </div>
      </div>
    </div>
  );
}
