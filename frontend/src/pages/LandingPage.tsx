import { type FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { joinWaitlist } from "../api/endpoints";
import { useAuth } from "../context/AuthContext";
import { extractErrorMessage } from "../utils/errors";
import { emailError } from "../utils/validation";

const PRO_PRICE_DISPLAY = (import.meta.env.VITE_PRO_PLAN_PRICE_DISPLAY as string | undefined) || "₹299/month";

const FEATURES = [
  { title: "GST-compliant invoicing", desc: "CGST/SGST, IGST, or zero-rated exports under LUT — computed automatically from your client's state and country." },
  { title: "Expense tracking", desc: "Manual entry or CSV bank-statement import, with input tax credit tracked per expense." },
  { title: "GST & income tax estimates", desc: "GSTR-1 and GSTR-3B pre-fill worksheets, plus a 44ADA presumptive income tax estimate — every filing season." },
  { title: "Recurring invoices", desc: "Weekly, monthly, or quarterly templates with optional auto-send, for retainer clients." },
  { title: "Dashboard & reports", desc: "Profit & loss, revenue trends, and top clients at a glance — export as CSV or PDF, or a read-only link for your CA." },
  { title: "Built for freelancers with global clients", desc: "Multi-currency invoicing and export-invoice handling, alongside domestic GST invoicing." },
];

export function LandingPage() {
  const { user } = useAuth();
  const [waitlistEmail, setWaitlistEmail] = useState("");
  const [waitlistError, setWaitlistError] = useState("");
  const [waitlistDone, setWaitlistDone] = useState(false);
  const [joiningWaitlist, setJoiningWaitlist] = useState(false);

  async function handleWaitlistSubmit(e: FormEvent) {
    e.preventDefault();
    const validationError = emailError(waitlistEmail);
    if (validationError) {
      setWaitlistError(validationError);
      return;
    }
    setJoiningWaitlist(true);
    setWaitlistError("");
    try {
      await joinWaitlist(waitlistEmail);
      setWaitlistDone(true);
    } catch (err) {
      setWaitlistError(extractErrorMessage(err, "Could not join the waitlist."));
    } finally {
      setJoiningWaitlist(false);
    }
  }

  return (
    <div className="landing-page">
      <header className="landing-header">
        <span className="landing-brand">Freelancer Finance OS</span>
        <nav className="landing-header-actions">
          {user ? (
            <Link className="btn btn-primary" to="/dashboard">Go to Dashboard</Link>
          ) : (
            <>
              <Link className="btn btn-link" to="/login">Log In</Link>
              <Link className="btn btn-primary" to="/register">Get Started Free</Link>
            </>
          )}
        </nav>
      </header>

      <section className="landing-hero">
        <h1>GST invoicing and bookkeeping, built for freelancers with international clients.</h1>
        <p className="landing-hero-subtitle">
          Create GST-compliant invoices, track expenses, and get your GSTR-1, GSTR-3B, and income
          tax estimates ready before every filing deadline — without spreadsheets.
        </p>
        <div className="landing-hero-actions">
          <Link className="btn btn-primary" to={user ? "/dashboard" : "/register"}>
            {user ? "Go to Dashboard" : "Get Started Free"}
          </Link>
          <a className="btn btn-secondary" href="#pricing">See Pricing</a>
        </div>
      </section>

      <section className="landing-features">
        {FEATURES.map((f) => (
          <div className="card landing-feature-card" key={f.title}>
            <h3>{f.title}</h3>
            <p className="page-subtitle">{f.desc}</p>
          </div>
        ))}
      </section>

      <section className="landing-pricing" id="pricing">
        <h2>Simple pricing</h2>
        <div className="landing-pricing-cards">
          <div className="card landing-pricing-card">
            <h3>Free</h3>
            <div className="landing-price">₹0</div>
            <p className="page-subtitle">Up to 5 invoices a month. Every other feature included.</p>
            <Link className="btn btn-secondary" to={user ? "/dashboard" : "/register"}>
              {user ? "Go to Dashboard" : "Start Free"}
            </Link>
          </div>
          <div className="card landing-pricing-card landing-pricing-card-highlight">
            <h3>Pro</h3>
            <div className="landing-price">{PRO_PRICE_DISPLAY}</div>
            <p className="page-subtitle">Unlimited invoices. Everything in Free, no monthly cap.</p>
            <Link className="btn btn-primary" to={user ? "/settings" : "/register"}>
              {user ? "Upgrade in Settings" : "Get Started"}
            </Link>
          </div>
        </div>
      </section>

      {!user && (
        <section className="landing-waitlist">
          <div className="card landing-waitlist-card">
            <h3>Not ready to sign up yet?</h3>
            <p className="page-subtitle">
              Leave your email and we'll let you know as soon as this is live for everyone.
            </p>
            {waitlistDone ? (
              <div className="alert alert-success">You're on the list — we'll email you when it's ready.</div>
            ) : (
              <form className="landing-waitlist-form" onSubmit={handleWaitlistSubmit} noValidate>
                <label className="sr-only" htmlFor="waitlist-email">Email</label>
                <input
                  id="waitlist-email" type="email" placeholder="you@example.com"
                  value={waitlistEmail} onChange={(e) => setWaitlistEmail(e.target.value)}
                  className={waitlistError ? "field-error-input" : ""}
                />
                <button className="btn btn-primary" type="submit" disabled={joiningWaitlist}>
                  {joiningWaitlist && <span className="btn-spinner" />}
                  {joiningWaitlist ? "Joining..." : "Notify Me"}
                </button>
              </form>
            )}
            {waitlistError && <span className="field-error-text">{waitlistError}</span>}
          </div>
        </section>
      )}
    </div>
  );
}
