import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { register } from "../api/endpoints";
import { GoogleSignInButton } from "../components/GoogleSignInButton";
import { useAuth } from "../context/AuthContext";
import { extractErrorMessage } from "../utils/errors";

export function RegisterPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await register(email, password, name);
      await login(email, password);
      navigate("/business-profile");
    } catch (err) {
      setError(extractErrorMessage(err, "Could not create your account."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={handleSubmit}>
        <h1>Freelancer Finance OS</h1>
        <p className="auth-subtitle">Create your account</p>

        {error && <div className="alert alert-error">{error}</div>}

        <label>Full name
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label>Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
        </label>

        <button className="btn btn-primary" type="submit" disabled={submitting}>
          {submitting ? "Creating account..." : "Sign up"}
        </button>

        <div className="page-subtitle" style={{ textAlign: "center" }}>or</div>
        <GoogleSignInButton />

        <p className="auth-switch">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </form>
    </div>
  );
}
