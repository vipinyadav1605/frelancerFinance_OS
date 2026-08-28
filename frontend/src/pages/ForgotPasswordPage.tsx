import { type FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { requestPasswordReset } from "../api/endpoints";
import { extractErrorMessage } from "../utils/errors";
import { emailError } from "../utils/validation";

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [fieldError, setFieldError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    const err = emailError(email);
    setFieldError(err);
    if (err) return;

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
          <form onSubmit={handleSubmit} noValidate style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {error && <div className="alert alert-error">{error}</div>}
            <label>Email
              <input
                type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                onBlur={() => setFieldError(emailError(email))}
                className={fieldError ? "field-error-input" : ""}
              />
              {fieldError && <span className="field-error-text">{fieldError}</span>}
            </label>
            <button className="btn btn-primary" type="submit" disabled={submitting}>
              {submitting && <span className="btn-spinner" />}
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
