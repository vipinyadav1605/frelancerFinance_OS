import { type FormEvent, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { confirmPasswordReset } from "../api/endpoints";
import { extractErrorMessage } from "../utils/errors";

export function ResetPasswordPage() {
  const { uid, token } = useParams<{ uid: string; token: string }>();
  const navigate = useNavigate();
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (!uid || !token) {
      setError("This reset link is malformed.");
      return;
    }
    setSubmitting(true);
    try {
      await confirmPasswordReset(uid, token, newPassword);
      setDone(true);
      setTimeout(() => navigate("/login"), 2000);
    } catch (err) {
      setError(extractErrorMessage(err, "This reset link is invalid or has expired."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>Reset Password</h1>

        {done ? (
          <div className="alert alert-success">Password reset. Redirecting to login...</div>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {error && <div className="alert alert-error">{error}</div>}
            <label>New password
              <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required minLength={8} />
            </label>
            <label>Confirm new password
              <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required minLength={8} />
            </label>
            <button className="btn btn-primary" type="submit" disabled={submitting}>
              {submitting ? "Resetting..." : "Reset Password"}
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
