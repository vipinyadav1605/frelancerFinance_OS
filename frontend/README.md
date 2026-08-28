# Freelancer Finance OS — Frontend

React + TypeScript (Vite) frontend for Phase 1 (see `03_PRD.pdf` in the Zyricon
folder for the functional requirements this implements: FR-1 through FR-6).

## Setup

```bash
cd frontend
npm install
cp .env.example .env   # defaults to http://127.0.0.1:8000/api, matching the backend README
npm run dev
```

App runs at `http://localhost:5173`. The backend must be running at the URL in
`VITE_API_BASE_URL` (see `../backend/README.md`) — including CORS: the backend's
`CORS_ALLOWED_ORIGINS` must include `http://localhost:5173`.

`VITE_GOOGLE_CLIENT_ID` is optional - leave it blank to hide the "Sign in with
Google" button entirely (see `.env.example` for where to get one; it must
match the backend's `GOOGLE_OAUTH_CLIENT_ID`).

## Pages

| Route | Purpose |
|---|---|
| `/` | Public marketing/pricing landing page (logged-out visitors) - shows "Go to Dashboard" instead of sign-up CTAs when already logged in |
| `/terms`, `/privacy` | Static legal pages, linked from the footer on every page |
| `/register`, `/login` | FR-1. `/register?ref=<code>` credits the referrer named by that code |
| `/auth/github/callback` | GitHub OAuth redirect target - exchanges the returned code for a session, then forwards to `/dashboard` |
| `/forgot-password`, `/reset-password/:uid/:token` | Password reset via emailed link |
| `/business-profile` | FR-2 |
| `/clients` | FR-3: list, add, edit clients |
| `/invoices` | FR-4/FR-5: invoice list with status filters |
| `/invoices/new` | FR-4/FR-5: create invoice, tax computed server-side |
| `/invoices/:id` | FR-6: view invoice, download PDF, send, mark paid |
| `/expenses` | Phase 2: manual expense entry, CSV bank-statement import with column mapping, filter by category/date |
| `/dashboard` | Phase 3/4: P&L, GST liability, 44ADA income tax estimate, GSTR-1 and GSTR-3B pre-fill summaries, CSV/PDF/GSTR-1 export - default page after login |
| `/recurring-invoices` | Phase 4: manage recurring invoice templates (weekly/monthly/quarterly, optional auto-send) |
| `/integrations` | Phase 5: manage API keys and outgoing webhook subscriptions |
| `/shared/:token` | Phase 5: public, no-login read-only report view (for a CA/collaborator) |
| `/settings` | Consolidated hub (tabs: Profile, Business, Security, Notifications, Integrations, Billing, Danger Zone) - reuses `BusinessProfilePage`/`IntegrationsPage` as tab content rather than duplicating them. `/business-profile` and `/integrations` still work standalone. |
| `/pay/:token` | Public, no-login client-facing invoice view/pay page (permanent link, from `Invoice.public_view_token`) |

## Notes

- JWT access/refresh tokens are stored in `localStorage` and auto-refreshed via
  an axios response interceptor (`src/api/client.ts`) on a 401. Logging out
  calls `/auth/logout/` to blacklist the refresh token server-side (not just
  a local `localStorage.clear()`) - see `api/endpoints.ts::logout()`.
- Tax type (CGST+SGST / IGST / export zero-rated) is always computed by the
  backend from the business profile's state and the client's state/country —
  the frontend only shows an informational note, it never decides tax logic.
- Build check: `npm run build` (runs `tsc -b` then `vite build`).
- Phase 5: the app is an installable PWA (`public/manifest.webmanifest` +
  `public/sw.js`, registered in `main.tsx`) - "Add to Home Screen" on mobile
  gives an app-like icon/window without a separate native codebase. The
  service worker only caches the static shell, never `/api/` responses.
- **Dark mode**: toggled in Settings > Profile, persisted in `localStorage`
  (`src/utils/theme.ts`), applied via a `data-theme` attribute on `<html>` -
  the whole design system is CSS custom properties (`index.css`), so the
  toggle just swaps the token values, no per-component dark-mode logic.
- **Notification bell** (`components/NotificationBell.tsx`) polls
  `/notifications/unread-count/` every 60s and lists recent notifications on
  click - not a websocket/push system, just periodic polling (adequate at
  this scale; revisit if real-time matters later).
- **Onboarding checklist** (`components/OnboardingChecklist.tsx`) shows on
  the Dashboard until business profile + a client + a sent invoice all exist,
  or until manually dismissed (remembered in `localStorage`).
- **Bulk actions**: multi-select + "mark selected as paid" on the invoice
  list, multi-select + "delete selected" on the expense list. Implemented as
  parallel calls to the existing single-item endpoints (`Promise.all`), not
  new bulk-specific backend endpoints - fine at solo-freelancer data volumes.
- **Pagination**: `/invoices` and `/expenses` now request/render a page at a
  time (`Previous`/`Next`, 25/page) - `listInvoices()`/`listExpenses()` return
  a `Paginated<T>` envelope (`{count, next, previous, results}`), not a plain
  array. Any new code reading these must use `.results`.
- **Global search** (`components/GlobalSearch.tsx`, in the Navbar) debounces
  (250ms) queries to `/search/` across invoices and clients.
- **Dashboard charts** (`components/DashboardCharts.tsx`, via `recharts`) are
  lazy-loaded with `React.lazy`/`Suspense` - recharts is ~110KB gzipped and
  only the Dashboard needs it, so it ships as its own chunk rather than
  bloating every page's initial load.
- **2FA login flow** is a single request either way: submit email+password;
  if the backend responds with `two_factor_required`, reveal an OTP field and
  resubmit with `otp_code` added (`pages/LoginPage.tsx`). Note: check that
  field for *truthiness*, not `=== true` - DRF's `ValidationError` coerces
  dict values into string-wrapped arrays (`["True"]`), not a bare boolean.
- **Social sign-in** (`components/SocialSignInButtons.tsx`, used on both
  Login and Register) renders Google/Microsoft/GitHub buttons and the "or"
  divider above them - but only for whichever providers actually have a
  `VITE_..._CLIENT_ID` set, and the divider itself disappears entirely if
  none do, so a plain email/password form never shows a floating "or" with
  nothing underneath it:
  - **Google** (`components/GoogleSignInButton.tsx`) loads Google's Identity
    Services script on demand and renders its own official button.
  - **Microsoft** (`components/MicrosoftSignInButton.tsx`) uses MSAL.js's
    popup sign-in flow. `@azure/msal-browser` is a large dependency
    (~60KB gzipped) - lazy-loaded (`React.lazy`/`Suspense` in
    `SocialSignInButtons.tsx`) so it only ships to a browser that actually
    needs it, not to every visitor of the login/register page.
  - **GitHub** (`components/GitHubSignInButton.tsx` + `pages/GitHubCallbackPage.tsx`,
    route `/auth/github/callback`) can't use a client-only token flow like
    the other two - GitHub's OAuth exchange needs a client secret, so the
    button just redirects to GitHub's own authorize page, and the callback
    page hands the returned `code` to the backend to finish the exchange.
    A random `state` value is round-tripped through `sessionStorage` to
    guard against CSRF on that redirect. The callback's effect is guarded
    with a `useRef` since a GitHub authorization code can only be exchanged
    once, and React 19's StrictMode double-invokes effects in dev.
- **Landing page** (`pages/LandingPage.tsx`, route `/`) is the only public
  page with its own header instead of the app `Navbar` (the Navbar renders
  nothing when logged out) - shows sign-up CTAs to visitors and a "Go to
  Dashboard" link if already logged in. The Pro price shown there is a pure
  display string (`VITE_PRO_PLAN_PRICE_DISPLAY`) - keep it in sync manually
  with whatever Razorpay Plan `RAZORPAY_PRO_MONTHLY_PLAN_ID` points to.
- **Growth loop**: the public invoice page (`/pay/:token`) and shared report
  page (`/shared/:token`) both end with a small "Powered by Freelancer
  Finance OS" line linking back to `/` - free distribution, since every
  invoice a user sends becomes a small ad to their client. Separately,
  Settings > Billing > "Refer a Freelancer" shows the user's own
  `/register?ref=<code>` link and how many people have used it - the backend
  grants a free month of Pro to the referrer when a referred signup upgrades
  (see `backend/README.md`'s "Referral reward" section).
- **Waitlist capture** on the landing page (logged-out visitors only): an
  email field posting to `/api/waitlist/`, for people who find the app before
  it's actually deployed anywhere - builds a launch-day list instead of
  starting from zero.
- **SEO**: `index.html` carries a real title/description and Open Graph/Twitter
  meta tags; `public/robots.txt` only allows `/`, `/terms`, `/privacy` (the
  rest are login-gated app pages with nothing worth indexing);
  `public/sitemap.xml` lists the three public pages. Both files use relative
  URLs - update them to your real domain once this is actually deployed.
- **Error tracking**: set `VITE_SENTRY_DSN` (create a free React project at
  [sentry.io](https://sentry.io)) to report unhandled frontend errors via
  `@sentry/react`. Left unset (the default), the import is fully dead-code-eliminated
  at build time - verified it adds zero bytes to the bundle unconfigured, and
  the SDK only ships once a real DSN is set. Independent of the backend's own
  `SENTRY_DSN`.

## Design system, toasts & validation

- **Design tokens** (`index.css` `:root`): colors, `--shadow-sm/md/lg`,
  `--radius-sm/md/lg`, and a shared `--ease` transition curve. Both light and
  dark palettes (and a `prefers-color-scheme` fallback for the brief window
  before `main.tsx`'s `initTheme()` runs) are defined as the same token set,
  so components never hardcode colors - swapping tokens is the whole theme.
- **Toasts** (`context/ToastContext.tsx`, `<ToastProvider>` wraps the app in
  `main.tsx` above `AuthProvider` so toasts survive route changes/logout):
  `const toast = useToast(); toast.success("...")` / `.error()` / `.info()`.
  Used for transient confirmations (saved, deleted, copied, toggled).
  Form-level errors stay as inline `.alert-error` banners next to the form
  that caused them - toasts are for things that don't need to stay on screen.
- **Field validation** (`utils/validation.ts` - plain functions, no form
  library): every auth/settings/client/expense/invoice form validates
  on blur and on submit, applying `.field-error-input` (red border) and a
  `.field-error-text` message under the field. Forms with custom validation
  set `noValidate` on the `<form>` to stop the browser's native tooltips from
  fighting with it. **Known scope trim**: invoice/recurring-invoice line-item
  table cells still rely on the backend's validation (surfaced in the
  top-of-form alert) rather than per-cell inline errors - keeps the table
  UI clean; the browser's native `required`/`min` attributes stay on those
  specific inputs as a soft hint even though the form's `noValidate` means
  they're not enforced.
- **Responsive**: navbar collapses to a hamburger menu below ~920px
  (`Navbar.tsx`'s `navbar-toggle`); `.dashboard-cards`/`.form-row` stack on
  narrow screens; every `<table>` is wrapped in a `.table-scroll` div
  (horizontal scroll) rather than rebuilt as a card-list per page - simpler
  and consistent across every table in the app.
- **Animations**: `prefers-reduced-motion: reduce` disables all of them
  globally. Otherwise: page fade-up on mount, card/button hover lift, toast
  slide-in/out, dropdown pop-in (notification bell, global search), a
  pulsing unread badge, and `.btn-spinner`/`.spinner-lg` loading spinners on
  every async button and page-loading state.
