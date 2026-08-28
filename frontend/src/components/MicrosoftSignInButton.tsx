import { PublicClientApplication } from "@azure/msal-browser";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const CLIENT_ID = import.meta.env.VITE_MICROSOFT_CLIENT_ID as string | undefined;

let msalInstance: PublicClientApplication | null = null;
let msalInitialized: Promise<PublicClientApplication> | null = null;

function getMsal(): Promise<PublicClientApplication> {
  if (!msalInitialized) {
    msalInstance = new PublicClientApplication({
      auth: {
        clientId: CLIENT_ID!,
        authority: "https://login.microsoftonline.com/common",
        redirectUri: window.location.origin,
      },
    });
    msalInitialized = msalInstance.initialize().then(() => msalInstance!);
  }
  return msalInitialized;
}

export function MicrosoftSignInButton() {
  const { loginWithMicrosoft } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (!CLIENT_ID) return null; // not configured on this deployment - hide the button entirely

  async function handleClick() {
    setError("");
    setLoading(true);
    try {
      const app = await getMsal();
      const result = await app.loginPopup({ scopes: ["openid", "profile", "email"] });
      await loginWithMicrosoft(result.idToken);
      navigate("/dashboard");
    } catch {
      setError("Microsoft sign-in failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "0.5rem" }}>
      <button type="button" className="btn btn-oauth btn-oauth-microsoft" onClick={handleClick} disabled={loading}>
        {loading && <span className="btn-spinner" />}
        {loading ? "Signing in..." : "Continue with Microsoft"}
      </button>
      {error && <div className="alert alert-error">{error}</div>}
    </div>
  );
}
