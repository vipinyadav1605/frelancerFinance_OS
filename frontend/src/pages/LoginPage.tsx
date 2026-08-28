import { AxiosError } from "axios";
import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { GoogleSignInButton } from "../components/GoogleSignInButton";
import { useAuth } from "../context/AuthContext";
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
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
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
      <form className="auth-card" onSubmit={handleSubmit}>
        <h1>Freelancer Finance OS</h1>
        <p className="auth-subtitle">Log in to your account</p>

        {error && <div className="alert alert-error">{error}</div>}

        <label>Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required disabled={needsOtp} />
        </label>
        <label>Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required disabled={needsOtp} />
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
          {submitting ? "Logging in..." : needsOtp ? "Verify Code" : "Log in"}
        </button>

        {!needsOtp && (
          <>
            <div className="page-subtitle" style={{ textAlign: "center" }}>or</div>
            <GoogleSignInButton />
          </>
        )}

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
