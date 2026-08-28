import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { GITHUB_OAUTH_STATE_STORAGE_KEY } from "../components/GitHubSignInButton";
import { useAuth } from "../context/AuthContext";
import { extractErrorMessage } from "../utils/errors";

export function GitHubCallbackPage() {
  const { loginWithGitHub } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [error, setError] = useState("");
  // React 19's StrictMode double-invokes effects in dev - a GitHub
  // authorization code can only be exchanged once, so a second call with the
  // same code would fail. This guard makes sure the exchange runs exactly once.
  const hasRun = useRef(false);

  useEffect(() => {
    if (hasRun.current) return;
    hasRun.current = true;

    const code = searchParams.get("code");
    const state = searchParams.get("state");
    const expectedState = sessionStorage.getItem(GITHUB_OAUTH_STATE_STORAGE_KEY);
    sessionStorage.removeItem(GITHUB_OAUTH_STATE_STORAGE_KEY);

    if (!code || !state || state !== expectedState) {
      setError("This GitHub sign-in link is invalid or has expired. Please try again.");
      return;
    }

    loginWithGitHub(code)
      .then(() => navigate("/dashboard"))
      .catch((err) => setError(extractErrorMessage(err, "GitHub sign-in failed. Please try again.")));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (error) {
    return (
      <div className="page">
        <div className="alert alert-error">{error}</div>
        <Link className="btn btn-secondary" to="/login">Back to Log In</Link>
      </div>
    );
  }

  return <div className="page-loading"><span className="spinner-lg" /> Signing in with GitHub...</div>;
}
