const CLIENT_ID = import.meta.env.VITE_GITHUB_CLIENT_ID as string | undefined;
export const GITHUB_OAUTH_STATE_STORAGE_KEY = "github_oauth_state";

export function GitHubSignInButton() {
  if (!CLIENT_ID) return null; // not configured on this deployment - hide the button entirely

  function handleClick() {
    // A random, one-time "state" value defends against CSRF on the OAuth
    // redirect - the callback page checks it matches before trusting the code.
    const state = crypto.randomUUID();
    sessionStorage.setItem(GITHUB_OAUTH_STATE_STORAGE_KEY, state);

    const params = new URLSearchParams({
      client_id: CLIENT_ID!,
      redirect_uri: `${window.location.origin}/auth/github/callback`,
      scope: "read:user user:email",
      state,
    });
    window.location.href = `https://github.com/login/oauth/authorize?${params.toString()}`;
  }

  return (
    <button type="button" className="btn btn-oauth btn-oauth-github" onClick={handleClick}>
      Continue with GitHub
    </button>
  );
}
