import { type FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { requestPasswordReset } from "../api/endpoints";
import { extractErrorMessage } from "../utils/errors";

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await requestPasswordReset(email);
      setDone(true);
    } catch (err) {
      setError(extractErrorMessage(err, "Something went wrong. Please try again."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>Forgot Password</h1>
        <p className="auth-subtitle">We'll email you a link to reset it.</p>

        {done ? (
          <div className="alert alert-success">
            If that email is registered, a reset link has been sent. Check your inbox.
          </div>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {error && <div className="alert alert-error">{error}</div>}
            <label>Email
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </label>
            <button className="btn btn-primary" type="submit" disabled={submitting}>
              {submitting ? "Sending..." : "Send Reset Link"}
            </button>
          </form>
        )}

        <p className="auth-switch">
          <Link to="/login">Back to login</Link>
        </p>
      </div>
    </div>
  );
}
