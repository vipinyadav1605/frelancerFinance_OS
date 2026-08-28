import { type FormEvent, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { confirmPasswordReset } from "../api/endpoints";
import { useToast } from "../context/ToastContext";
import { extractErrorMessage } from "../utils/errors";
import { confirmPasswordError, passwordError } from "../utils/validation";

export function ResetPasswordPage() {
  const { uid, token } = useParams<{ uid: string; token: string }>();
  const navigate = useNavigate();
  const toast = useToast();
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState({ newPassword: "", confirmPassword: "" });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    const errors = {
      newPassword: passwordError(newPassword),
      confirmPassword: confirmPasswordError(newPassword, confirmPassword),
    };
    setFieldErrors(errors);
    if (errors.newPassword || errors.confirmPassword) return;

    if (!uid || !token) {
      setError("This reset link is malformed.");
      return;
    }
    setSubmitting(true);
    try {
      await confirmPasswordReset(uid, token, newPassword);
      setDone(true);
      toast.success("Password reset successfully.");
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
          <form onSubmit={handleSubmit} noValidate style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {error && <div className="alert alert-error">{error}</div>}
            <label>New password
              <input
                type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)}
                onBlur={() => setFieldErrors((f) => ({ ...f, newPassword: passwordError(newPassword) }))}
                className={fieldErrors.newPassword ? "field-error-input" : ""}
              />
              {fieldErrors.newPassword && <span className="field-error-text">{fieldErrors.newPassword}</span>}
            </label>
            <label>Confirm new password
              <input
                type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)}
                onBlur={() => setFieldErrors((f) => ({ ...f, confirmPassword: confirmPasswordError(newPassword, confirmPassword) }))}
                className={fieldErrors.confirmPassword ? "field-error-input" : ""}
              />
              {fieldErrors.confirmPassword && <span className="field-error-text">{fieldErrors.confirmPassword}</span>}
            </label>
            <button className="btn btn-primary" type="submit" disabled={submitting}>
              {submitting && <span className="btn-spinner" />}
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
