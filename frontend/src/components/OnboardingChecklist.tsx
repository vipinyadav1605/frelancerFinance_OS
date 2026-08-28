import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getOnboardingStatus } from "../api/endpoints";
import type { OnboardingStatus } from "../types";

const DISMISS_KEY = "ffos_onboarding_dismissed";

function ChecklistItem({ done, to, children }: { done: boolean; to: string; children: React.ReactNode }) {
  return (
    <li className={`onboarding-item ${done ? "onboarding-item-done" : ""}`}>
      <span className={`onboarding-check ${done ? "onboarding-check-done" : "onboarding-check-pending"}`}>
        {done ? "✓" : ""}
      </span>
      {done ? <span>{children}</span> : <Link to={to}>{children}</Link>}
    </li>
  );
}

export function OnboardingChecklist() {
  const [status, setStatus] = useState<OnboardingStatus | null>(null);
  const [dismissed, setDismissed] = useState(() => localStorage.getItem(DISMISS_KEY) === "1");

  useEffect(() => {
    if (dismissed) return;
    getOnboardingStatus().then(setStatus).catch(() => {});
  }, [dismissed]);

  if (dismissed || !status) return null;

  const allDone = status.has_business_profile && status.has_client && status.has_sent_invoice;
  if (allDone) return null;

  function dismiss() {
    localStorage.setItem(DISMISS_KEY, "1");
    setDismissed(true);
  }

  return (
    <div className="card">
      <div className="page-header-row">
        <h3 style={{ marginBottom: 0 }}>Getting Started</h3>
        <button className="btn-link" onClick={dismiss}>Hide</button>
      </div>
      <ul className="onboarding-checklist">
        <ChecklistItem done={status.has_business_profile} to="/settings?tab=business">
          Set up your business profile
        </ChecklistItem>
        <ChecklistItem done={status.has_client} to="/clients">
          Add your first client
        </ChecklistItem>
        <ChecklistItem done={status.has_invoice} to="/invoices/new">
          Create your first invoice
        </ChecklistItem>
        <ChecklistItem done={status.has_sent_invoice} to="/invoices">
          Send an invoice
        </ChecklistItem>
      </ul>
    </div>
  );
}
