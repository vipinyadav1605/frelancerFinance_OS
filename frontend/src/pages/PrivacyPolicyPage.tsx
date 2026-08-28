export function PrivacyPolicyPage() {
  return (
    <div className="page legal-page">
      <div className="page-header">
        <h1>Privacy Policy</h1>
        <p className="page-subtitle">Last updated: 28 August 2026</p>
      </div>

      <div className="card">
        <h3>1. What we collect</h3>
        <p>
          Account details (email, password hash), your business profile (business name, GSTIN,
          PAN, state), your clients' details, invoices, and expenses you enter. If you use Google
          Sign-In, we receive your name and email from Google. If you subscribe to Pro, Razorpay
          processes your payment — we store your subscription status, not your card details.
        </p>

        <h3>2. Why we collect it</h3>
        <p>
          Solely to provide the service: generating GST-compliant invoices, computing GST and
          income tax estimates, sending you transactional emails (password resets, invoice
          delivery to your clients, payment reminders), and enforcing plan limits.
        </p>

        <h3>3. Who else sees it</h3>
        <p>
          We don't sell your data. It's shared only with the service providers needed to run the
          app: our database and hosting provider, Razorpay (for Pro plan payments), Google (only
          if you use Sign in with Google), and our email delivery provider (for sending the emails
          above). Anyone you send a public invoice or report link to can view what that specific
          link exposes — nothing else.
        </p>

        <h3>4. Your controls</h3>
        <p>
          From Settings, you can enable two-factor authentication, download an export of your
          data, or permanently delete your account and all associated data. Deleting your account
          is irreversible.
        </p>

        <h3>5. Retention</h3>
        <p>
          We keep your data for as long as your account is active, so your invoice history and GST
          records remain available for filing and audit purposes. Deleting your account removes it
          promptly, except where we're legally required to retain billing records for a limited
          period.
        </p>

        <h3>6. Security</h3>
        <p>
          Passwords are hashed, not stored in plain text. Sessions use short-lived tokens with
          server-side revocation on logout. We support optional two-factor authentication for an
          extra layer of protection on your account.
        </p>

        <h3>7. Changes</h3>
        <p>We may update this policy as the service evolves; material changes will be reflected here with an updated date.</p>

        <h3>8. Contact</h3>
        <p>Questions about this policy, or to request your data: <a href="mailto:vvvyadav223221@gmail.com">vvvyadav223221@gmail.com</a></p>
      </div>
    </div>
  );
}
