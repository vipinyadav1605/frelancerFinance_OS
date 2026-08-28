# Freelancer Finance OS — Backend

Django + Django REST Framework + PostgreSQL backend implementing Phase 0/1 of the
roadmap (see `01_Product_Roadmap.pdf`, `02_Technical_Design_HLD_LLD.pdf`, and
`03_PRD.pdf` in the Zyricon folder for full context).

## Setup

```bash
cd backend
python -m venv venv
./venv/Scripts/activate        # Windows
pip install -r requirements.txt
cp .env.example .env           # then edit .env with real values
```

### Database

This project uses PostgreSQL. One-time setup (run once, in `psql` or pgAdmin, as
your postgres superuser):

```sql
CREATE DATABASE freelancer_finance_os;
CREATE USER ffos_app WITH PASSWORD 'choose_a_strong_password_here';
GRANT ALL PRIVILEGES ON DATABASE freelancer_finance_os TO ffos_app;
ALTER DATABASE freelancer_finance_os OWNER TO ffos_app;
\c freelancer_finance_os
GRANT ALL ON SCHEMA public TO ffos_app;
```

Then set `DATABASE_URL` in `.env` to match:

```
DATABASE_URL=postgres://ffos_app:choose_a_strong_password_here@localhost:5432/freelancer_finance_os
```

If `DATABASE_URL` is left unset, the project falls back to a local SQLite file
(`db.sqlite3`) — useful for quick local iteration, but the real target is Postgres.

### Run

```bash
python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver
```

API is served at `http://127.0.0.1:8000/api/`. Admin at `/admin/`.

### Tests

```bash
python manage.py test
```

The most important test suites are `invoicing/tests/test_tax.py` (GST
tax-determination and calculation logic, PRD FR-4) and
`expenses/tests/test_csv_import.py` (CSV parsing/auto-categorization, Phase 2).

### Scheduled jobs

Run daily (e.g. via the hosting platform's cron feature):

```bash
python manage.py update_overdue_invoices     # Phase 1: mark invoices overdue (also fires invoice.overdue webhooks)
python manage.py send_payment_reminders      # Phase 3: email overdue reminders
python manage.py generate_recurring_invoices # Phase 4: generate due recurring invoices
```

## API summary

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/auth/register/` | POST | FR-1 signup (rate-limited: 5/hour/IP) |
| `/api/auth/login/` | POST | FR-1 login, returns access + refresh JWT (rate-limited: 10/min/IP) |
| `/api/auth/refresh/` | POST | refresh access token |
| `/api/auth/logout/` | POST | blacklists the given refresh token (`{"refresh": "..."}`) |
| `/api/auth/password-reset/` | POST | request a reset email (`{"email": "..."}`, rate-limited: 5/hour/IP) |
| `/api/auth/password-reset-confirm/` | POST | `{"uid", "token", "new_password"}` from the emailed link |
| `/api/auth/me/` | GET | current user info |
| `/api/auth/business-profile/` | GET/PUT | FR-2 |
| `/api/clients/` | GET/POST | FR-3 |
| `/api/clients/{id}/` | GET/PUT/PATCH/DELETE | FR-3 |
| `/api/invoices/` | GET/POST | FR-4/FR-5 (list supports `?status=` and `?client=`) |
| `/api/invoices/{id}/` | GET | invoice detail |
| `/api/invoices/{id}/send/` | POST | FR-6: create payment link + email invoice |
| `/api/invoices/{id}/mark-paid/` | POST | FR-6: manual payment fallback |
| `/api/webhooks/razorpay/` | POST | Razorpay payment webhook (signature-verified) |
| `/api/expense-categories/` | GET/POST | Phase 2: list/add expense categories (defaults seeded on signup) |
| `/api/expenses/` | GET/POST | Phase 2: list (supports `?category=`, `?date_from=`, `?date_to=`) / manually add an expense |
| `/api/expenses/import-csv/` | POST | Phase 2: upload a bank/UPI CSV with column mapping, auto-categorized |
| `/api/bank-statement-imports/` | GET | Phase 2: history of CSV imports |
| `/api/reports/profit-loss/` | GET | Phase 3: P&L + GST + income tax estimate (`?period_start=&period_end=`) |
| `/api/reports/profit-loss/export/` | GET | Phase 3: CSV/PDF export (`?export_format=csv\|pdf`) |
| `/api/reports/gstr1-prefill/` | GET | Phase 4: GSTR-1 B2B/B2C/Exports bucket summary |
| `/api/reports/gstr1-prefill/export/` | GET | Phase 4: downloadable GSTR-1 pre-fill worksheet (CSV) |
| `/api/recurring-invoices/` | GET/POST | Phase 4: recurring invoice templates |
| `/api/recurring-invoices/{id}/` | GET/PATCH/DELETE | Phase 4: manage one template |
| `/api/invoicing/exchange-rate/` | GET | Phase 4: live FX rate suggestion (`?currency=USD\|EUR\|GBP`) |
| `/api/api-keys/` | GET/POST | Phase 5: personal API keys (raw key shown once, on create) |
| `/api/api-keys/{id}/` | DELETE | Phase 5: revoke a key |
| `/api/webhooks/` | GET/POST | Phase 5: outgoing webhook subscriptions (`invoice.paid`/`invoice.overdue`/`expense.created`) |
| `/api/webhooks/{id}/` | GET/PATCH/DELETE | Phase 5: manage one subscription, incl. recent delivery log |
| `/api/report-share-links/` | GET/POST | Phase 5: create an expiring read-only report link |
| `/api/report-share-links/{id}/` | DELETE | Phase 5: revoke a share link |
| `/api/shared/report/{token}/` | GET | Phase 5: public (no auth) read-only view of a shared report |
| `/api/auth/change-password/` | POST | Settings > Security: `{"current_password", "new_password"}` |
| `/api/auth/change-email/` | POST | Settings > Security: `{"new_email", "current_password"}` |
| `/api/auth/delete-account/` | POST | Settings > Danger Zone: `{"current_password"}`, permanently deletes everything |
| `/api/auth/notification-preference/` | GET/PUT | Settings > Notifications: toggle emailed notifications |
| `/api/auth/onboarding-status/` | GET | drives the Dashboard's first-run setup checklist |
| `/api/auth/data-export/` | GET | Settings > Danger Zone: zip of clients/invoices/expenses CSVs |
| `/api/notifications/` | GET | in-app notification bell + activity history |
| `/api/notifications/unread-count/` | GET | for the bell icon's badge |
| `/api/notifications/{id}/mark-read/` | POST | mark one notification read |
| `/api/notifications/mark-all-read/` | POST | mark all notifications read |

## Security

- **Auth**: JWT (30-min access / 7-day refresh, rotated on use). Refresh tokens
  are blacklisted on rotation and on `/auth/logout/` (`token_blacklist` app) -
  without this, a stolen old refresh token could still be replayed after
  "logout". Login/register/password-reset are rate-limited (see API table)
  against brute-force/credential-stuffing and email-bombing.
- **Password reset**: standard Django signed-token flow (`accounts/services/password_reset.py`),
  emailed as a link into the SPA. The request endpoint always returns 200
  whether or not the email is registered, to avoid leaking which emails have
  accounts. Token is invalidated automatically once the password actually
  changes (it's a hash of the user's pk + password hash + timestamp).
- **Webhook SSRF protection**: a webhook subscription's URL is user-supplied,
  but the *server* makes the outgoing request - without a check, that's SSRF
  (pointing it at `localhost`, an internal service, or a cloud metadata
  endpoint). `integrations/services/url_safety.py` resolves the hostname and
  rejects private/loopback/link-local/reserved IPs, checked both at
  subscription-creation time and again immediately before every delivery
  (DNS can change between the two - "DNS rebinding").
- **Input validation**: GSTIN/PAN are pattern-validated (`accounts/validators.py`,
  layout-checked, not full mod-36 checksum), and file uploads (receipts, CSV
  imports) are size-capped (5 MB) and content-type-checked.
- **Production settings**: `DEBUG=False` refuses to start on the placeholder
  `SECRET_KEY`, and turns on `SECURE_SSL_REDIRECT`/HSTS/secure-cookie settings
  automatically (see the bottom of `config/settings.py` - review
  `SECURE_PROXY_SSL_HEADER` for your specific host before deploying).
- **Tests use a fast (MD5) password hasher** (`config/settings.py`, gated on
  `"test" in sys.argv`) - only affects `manage.py test`, never runtime. Real
  PBKDF2 hashing in every `create_user()`/login() call was costing minutes of
  test suite time for zero benefit against a throwaway test DB.

## Settings, notifications & activity history

- **Account deletion order matters**: `Client` and `ExpenseCategory` use
  `on_delete=PROTECT` on their children (so a client/category can't be
  silently deleted out from under historical invoices/expenses). Deleting a
  user therefore deletes `Invoice`/`RecurringInvoiceProfile`/`Expense` first,
  then the user (which cascades everything else) - see
  `accounts/services/account_deletion.py`'s docstring. Don't call `user.delete()`
  directly anywhere new without going through that service.
- **In-app notifications double as the activity log** - "notifications" and
  "audit log" were merged into one `notifications.Notification` model rather
  than building two parallel systems: every notification IS a history entry
  (read or not), and the bell icon just surfaces the unread ones. Fired on
  invoice paid/overdue, recurring-invoice generation, and webhook failures.
- **Emailed notifications are separately togglable** from in-app ones
  (`accounts.models.NotificationPreference`) - in-app notifications always
  fire; only the email side (payment confirmation, webhook failure alerts)
  respects the user's Settings > Notifications preference.
- **Customizable email sign-off** (`BusinessProfile.email_signoff`) is the
  intentionally-scoped version of "customizable email templates" - a full
  template engine with arbitrary variable interpolation would be a much
  bigger feature than a solo freelancer's real need here (personalizing how
  invoice emails sound to their clients).

## Known limitations (by design, for MVP)

- Razorpay payment links are created in INR (see comment in
  `invoicing/services/payments.py`) — a foreign-currency invoice's client pays
  the INR equivalent unless/until international payments are set up with Razorpay.
- Overdue-status updates run via a management command, not a background worker
  (matches the "cron first, Celery+Redis later" approach in Document 2).
- Email uses Django's console backend by default (prints to the terminal) —
  set a real `EMAIL_BACKEND`/SMTP config in `.env` before going live.
- Live bank sync (auto-importing transactions) was scoped out of Phase 4 - it
  needs a paid RBI Account Aggregator integration (e.g. Setu/Perfios), which
  costs more per month than this project's total ₹10,000 budget. CSV import
  (Phase 2) remains the supported way to bring in bank/UPI transactions.
- `generate_recurring_invoices` only generates the latest due cycle per run,
  it does not backfill missed cycles if the cron job was down for a while.
- The GSTR-1 export is a working paper (CSV) to speed up manual filing, not a
  GSTN-schema file - it does not integrate with the GST portal's e-filing API.
- "Team access" (Phase 5) was scoped down from full multi-user accounts/roles
  to expiring, read-only, no-login-required report share links - a single
  freelancer's real need is occasionally showing a report to their CA, not a
  full RBAC system. See `reports/models.py::ReportShareLink` docstring.
- Webhooks are delivered synchronously and best-effort (no retry queue, no
  Celery/Redis) - a slow/broken endpoint never blocks the request that
  triggered it, but a delivery that fails once is not automatically retried.
  Check `WebhookDelivery` rows (surfaced in the Integrations page) to debug.
- "Mobile" (Phase 5) was scoped down from a native app to an installable PWA
  (manifest + minimal service worker) - a solo dev + ₹10,000 budget can't
  support a separate React Native/Flutter codebase. The service worker never
  caches `/api/` responses, only the static app shell, so financial data is
  always fetched fresh.
