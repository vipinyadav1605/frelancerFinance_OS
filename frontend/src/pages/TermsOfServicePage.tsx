export function TermsOfServicePage() {
  return (
    <div className="page legal-page">
      <div className="page-header">
        <h1>Terms of Service</h1>
        <p className="page-subtitle">Last updated: 28 August 2026</p>
      </div>

      <div className="card">
        <h3>1. What this is</h3>
        <p>
          Freelancer Finance OS ("we", "the service") is a GST invoicing and bookkeeping tool for
          freelancers. By creating an account, you agree to these terms.
        </p>

        <h3>2. Your account</h3>
        <p>
          You're responsible for the accuracy of the invoices, expenses, and business details you
          enter, and for keeping your login credentials (including any two-factor authentication
          setup) confidential. Notify us if you suspect unauthorized access to your account.
        </p>

        <h3>3. Not tax or legal advice</h3>
        <p>
          GST liability, GSTR-1/GSTR-3B pre-fill worksheets, and income tax (Section 44ADA)
          estimates shown in this app are working papers to speed up your own filing — they are
          not filed returns and not a substitute for advice from a qualified Chartered Accountant.
          Always verify figures independently before filing with the GST portal or the Income Tax
          Department.
        </p>

        <h3>4. Plans and billing</h3>
        <p>
          The Free plan is limited to a set number of invoices per month; the Pro plan removes
          that limit for a recurring subscription fee, billed via Razorpay. You can cancel anytime
          from Settings — your plan remains active until the end of the current billing period.
          We don't offer prorated refunds for partial billing periods.
        </p>

        <h3>5. Public links</h3>
        <p>
          Invoices and reports you choose to share generate a link that anyone with the link can
          view, without logging in (e.g. a client-facing invoice page, or a read-only report link
          for your CA). You're responsible for only sharing those links with their intended
          recipient.
        </p>

        <h3>6. Availability</h3>
        <p>
          This service is provided "as is", without uptime guarantees. We aim to keep your data
          available and intact, but you should keep your own copies of anything critical (e.g. via
          the CSV/PDF export features) rather than relying on this app as your sole record.
        </p>

        <h3>7. Termination</h3>
        <p>
          You may delete your account at any time from Settings &gt; Danger Zone, which permanently
          removes your data. We may suspend an account that violates these terms or is used for
          unlawful purposes.
        </p>

        <h3>8. Changes</h3>
        <p>We may update these terms as the service evolves. Continued use after a change means you accept the update.</p>

        <h3>9. Contact</h3>
        <p>Questions about these terms: <a href="mailto:vvvyadav223221@gmail.com">vvvyadav223221@gmail.com</a></p>
      </div>
    </div>
  );
}
