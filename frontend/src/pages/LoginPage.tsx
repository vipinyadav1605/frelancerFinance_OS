import { AxiosError } from "axios";
import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { SocialSignInButtons } from "../components/SocialSignInButtons";
import { useAuth } from "../context/AuthContext";
import { emailError, requiredError } from "../utils/validation";
import { extractErrorMessage } from "../utils/errors";

function isTwoFactorRequired(err: unknown): boolean {
  // DRF's ValidationError coerces every dict value (even booleans) into a
  // string-wrapped array - the real response is `"two_factor_required": ["True"]`,
  // not the bare boolean `true`, so check truthiness/presence rather than `=== true`.
  return err instanceof AxiosError && Boolean(err.response?.data?.two_factor_required);
}

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [needsOtp, setNeedsOtp] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");

    if (!needsOtp) {
      const errors = { email: emailError(email), password: requiredError(password, "Password") };
      setFieldErrors(errors);
      if (errors.email || errors.password) return;
    }

    setSubmitting(true);
    try {
      await login(email, password, needsOtp ? otpCode : undefined);
      navigate("/dashboard");
    } catch (err) {
      if (isTwoFactorRequired(err)) {
        setNeedsOtp(true);
        setError("");
      } else {
        setError(extractErrorMessage(err, "Login failed. Check your email and password."));
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={handleSubmit} noValidate>
        <h1>Freelancer Finance OS</h1>
        <p className="auth-subtitle">Log in to your account</p>

        {error && <div className="alert alert-error">{error}</div>}

        <label>Email
          <input
            type="email" value={email} onChange={(e) => setEmail(e.target.value)} disabled={needsOtp}
            onBlur={() => setFieldErrors((f) => ({ ...f, email: emailError(email) }))}
            className={fieldErrors.email ? "field-error-input" : ""}
          />
          {fieldErrors.email && <span className="field-error-text">{fieldErrors.email}</span>}
        </label>
        <label>Password
          <input
            type="password" value={password} onChange={(e) => setPassword(e.target.value)} disabled={needsOtp}
            onBlur={() => setFieldErrors((f) => ({ ...f, password: requiredError(password, "Password") }))}
            className={fieldErrors.password ? "field-error-input" : ""}
          />
          {fieldErrors.password && <span className="field-error-text">{fieldErrors.password}</span>}
        </label>

        {needsOtp && (
          <label>Two-factor authentication code
            <input
              type="text" inputMode="numeric" maxLength={6} value={otpCode}
              onChange={(e) => setOtpCode(e.target.value)} placeholder="6-digit code" autoFocus required
            />
          </label>
        )}

        <button className="btn btn-primary" type="submit" disabled={submitting}>
          {submitting && <span className="btn-spinner" />}
          {submitting ? "Logging in..." : needsOtp ? "Verify Code" : "Log in"}
        </button>

        {!needsOtp && <SocialSignInButtons />}

        <p className="auth-switch">
          <Link to="/forgot-password">Forgot password?</Link>
        </p>
        <p className="auth-switch">
          Don't have an account? <Link to="/register">Sign up</Link>
        </p>
      </form>
    </div>
  );
}
