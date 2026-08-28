import { lazy, Suspense } from "react";
import { GitHubSignInButton } from "./GitHubSignInButton";
import { GoogleSignInButton } from "./GoogleSignInButton";

// @azure/msal-browser is a large dependency (~60KB gzipped) - lazy-loaded so
// it only ships to someone whose login/register page actually needs it
// (VITE_MICROSOFT_CLIENT_ID set), not to every visitor on every page load.
const MicrosoftSignInButton = lazy(() =>
  import("./MicrosoftSignInButton").then((m) => ({ default: m.MicrosoftSignInButton })),
);

const MICROSOFT_CONFIGURED = Boolean(import.meta.env.VITE_MICROSOFT_CLIENT_ID);

// Each button below already hides itself when its own provider isn't
// configured (no VITE_..._CLIENT_ID set) - this also skips the "or" divider
// entirely when NONE of them are configured, so a plain email/password form
// never shows a floating "or" with nothing underneath it.
const ANY_PROVIDER_CONFIGURED = Boolean(
  import.meta.env.VITE_GOOGLE_CLIENT_ID ||
  MICROSOFT_CONFIGURED ||
  import.meta.env.VITE_GITHUB_CLIENT_ID,
);

export function SocialSignInButtons() {
  if (!ANY_PROVIDER_CONFIGURED) return null;

  return (
    <>
      <div className="auth-divider"><span>or</span></div>
      <div className="social-signin-buttons">
        <GoogleSignInButton />
        {MICROSOFT_CONFIGURED && (
          <Suspense fallback={null}>
            <MicrosoftSignInButton />
          </Suspense>
        )}
        <GitHubSignInButton />
      </div>
    </>
  );
}
