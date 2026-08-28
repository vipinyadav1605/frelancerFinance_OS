import { type FormEvent, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { register } from "../api/endpoints";
import { SocialSignInButtons } from "../components/SocialSignInButtons";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { extractErrorMessage } from "../utils/errors";
import { confirmPasswordError, emailError, passwordError, requiredError } from "../utils/validation";

interface FieldErrors {
  name: string;
  email: string;
  password: string;
  confirmPassword: string;
}

const NO_ERRORS: FieldErrors = { name: "", email: "", password: "", confirmPassword: "" };

export function RegisterPage() {
  const { login } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const referredByCode = searchParams.get("ref") || undefined;
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>(NO_ERRORS);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function validate(): FieldErrors {
    return {
      name: requiredError(name, "Full name"),
      email: emailError(email),
      password: passwordError(password),
      confirmPassword: confirmPasswordError(password, confirmPassword),
    };
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    const errors = validate();
    setFieldErrors(errors);
    if (Object.values(errors).some(Boolean)) return;

    setSubmitting(true);
    try {
      await register(email, password, name, referredByCode);
      await login(email, password);
      toast.success("Account created — welcome aboard!");
      navigate("/business-profile");
    } catch (err) {
      setError(extractErrorMessage(err, "Could not create your account."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={handleSubmit} noValidate>
        <h1>Freelancer Finance OS</h1>
        <p className="auth-subtitle">Create your account</p>

        {error && <div className="alert alert-error">{error}</div>}
        {referredByCode && <div className="alert alert-info">You were referred by a friend — welcome!</div>}

        <label>Full name
          <input
            value={name} onChange={(e) => setName(e.target.value)}
            onBlur={() => setFieldErrors((f) => ({ ...f, name: requiredError(name, "Full name") }))}
            className={fieldErrors.name ? "field-error-input" : ""}
          />
          {fieldErrors.name && <span className="field-error-text">{fieldErrors.name}</span>}
        </label>
        <label>Email
          <input
            type="email" value={email} onChange={(e) => setEmail(e.target.value)}
            onBlur={() => setFieldErrors((f) => ({ ...f, email: emailError(email) }))}
            className={fieldErrors.email ? "field-error-input" : ""}
          />
          {fieldErrors.email && <span className="field-error-text">{fieldErrors.email}</span>}
        </label>
        <label>Password
          <input
            type="password" value={password} onChange={(e) => setPassword(e.target.value)}
            onBlur={() => setFieldErrors((f) => ({ ...f, password: passwordError(password) }))}
            className={fieldErrors.password ? "field-error-input" : ""}
          />
          {fieldErrors.password ? (
            <span className="field-error-text">{fieldErrors.password}</span>
          ) : (
            <span className="field-hint-text">At least 8 characters.</span>
          )}
        </label>
        <label>Confirm password
          <input
            type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)}
            onBlur={() => setFieldErrors((f) => ({ ...f, confirmPassword: confirmPasswordError(password, confirmPassword) }))}
            className={fieldErrors.confirmPassword ? "field-error-input" : ""}
          />
          {fieldErrors.confirmPassword && <span className="field-error-text">{fieldErrors.confirmPassword}</span>}
        </label>

        <button className="btn btn-primary" type="submit" disabled={submitting}>
          {submitting && <span className="btn-spinner" />}
          {submitting ? "Creating account..." : "Sign up"}
        </button>

        <SocialSignInButtons />

        <p className="auth-switch">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </form>
    </div>
  );
}
