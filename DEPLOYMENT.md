# Deploying: backend on Back4app Containers, frontend on Vercel

- **Backend** — a Back4app Containers app, built from `backend/Dockerfile`
- **Database** — a Neon free Postgres instance (Back4app Containers has no
  bundled managed Postgres on its free tier)
- **Frontend** — a Vercel project (Vite build output)

This is our third pick this round: Render's free web-service tier now
requires available credit, and Koyeb discontinued its free tier entirely
after being acquired by Mistral AI in Feb 2026 (it's pivoting to enterprise
AI-inference hosting). Back4app Containers is confirmed free with no credit
card as of Aug 2026, but it's less documented than Render/Koyeb were, so a
couple of steps below are marked **(verify)** — if what you see in the
dashboard doesn't match, tell me and I'll correct this file.

Back4app's unrestricted container networking (unlike a whitelisted host such
as PythonAnywhere) matters specifically for this project: Razorpay API calls
and Google OAuth token verification need to reach arbitrary external hosts.

Because free-tier terms keep shifting between providers, the backend is now
packaged as a plain `Dockerfile` (built and run-tested locally against the
real app - not guessed) rather than relying on any one platform's buildpack
magic. That makes it portable to whatever host is still free next time this
happens: Back4app, Google Cloud Run, or anywhere else that runs a container
from a Dockerfile.

Both dashboards need your login, so this is a guide to follow there.
Everything on the repo side is already prepped — see "What's already done"
below. Both repos are private, which is fine: Back4app and Vercel each
connect via a GitHub App you install and scope to only the specific repo(s)
you pick — nobody else gets read access, and nothing becomes public by
deploying it.

## What's already done in this repo

- `backend/Dockerfile` — installs `requirements.txt`, then at container
  start runs `migrate` → `collectstatic` → `gunicorn`, in that order. Built
  and verified locally: migrations apply cleanly (including all app
  migrations - accounts, billing, clients, expenses, etc.), static files
  collect, `/api/` returns `401` as expected (auth required), whitenoise
  serves admin static files.
- `backend/.dockerignore` — keeps `venv/`, `fvenv/`, `.env`, `db.sqlite3`,
  `media/` out of the image.
- `whitenoise` serves Django's own admin static files, no separate static
  host needed.
- `config/settings.py`: `SECURE_PROXY_SSL_HEADER` already wired for when
  `DJANGO_DEBUG=False` (Back4app's proxy should set `X-Forwarded-Proto`,
  same as every other platform we've tried this round — **verify** this
  once deployed by confirming you're not stuck in a redirect loop).
- `frontend/vercel.json` — rewrites every path to `/index.html`, so
  refreshing a client-side route (e.g. `/dashboard`) doesn't 404 on Vercel.
- `gunicorn` was already in `requirements.txt` from earlier.

`backend/build.sh` and `backend/.python-version` (from the Render/Koyeb
attempts) are no longer used — the Dockerfile replaces both. Harmless to
leave in place.

**Before you start**: commit and push — Back4app and Vercel both build from
your GitHub repo, so nothing here takes effect until it's pushed.

```
git add backend/Dockerfile backend/.dockerignore frontend/vercel.json
git commit -m "Add Dockerfile, switch deployment target to Back4app + Vercel"
git push
```

## Step 1 — Create the Neon Postgres database

1. [neon.tech](https://neon.tech) → sign up (GitHub login works, no credit
   card) → **Create a project**.
2. Name it something like `zyricon-finance-os`. Pick a region close to you.
3. Once created, copy the **Direct connection** string (not "Pooled" — a
   single gunicorn process doesn't need PgBouncer). It looks like:
   `postgresql://<user>:<password>@<host>.neon.tech/<dbname>?sslmode=require`
4. Free tier: 0.5GB storage, auto-suspends after a few minutes idle (short
   wake-up delay on the next request, no hard time limit like Render's free
   Postgres had).

## Step 2 — Create the backend app on Back4app Containers

1. [back4app.com](https://back4app.com) → sign up (no credit card) →
   **Containers** → **Connect GitHub** → grant access to **only this repo**.
   (If you already used a personal Back4app account for Zyricon_web's
   backend, that's fine — Back4app doesn't have Koyeb's one-instance-per-
   account limit as far as documented; if you do hit a cap, a second free
   account with a different email is the fallback.)
2. Select the repo, then configure the app:
   - **App name**: e.g. `zyricon-finance-os`
   - **Branch**: `main`
   - **Root directory**: `backend` (this is what makes it find
     `backend/Dockerfile` instead of expecting one at the repo root)
   - **Port** **(verify)**: the Dockerfile listens on `8000` — if Back4app's
     form asks for a port number, enter `8000`. If it instead expects your
     app to read a `PORT` env var it injects, our Dockerfile already
     supports that too (`--bind 0.0.0.0:${PORT:-8000}`), so either way
     should work without editing the Dockerfile.
3. Environment variables — set all of these:

   | Key | Value |
   |---|---|
   | `DJANGO_SECRET_KEY` | generate one: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
   | `DJANGO_DEBUG` | `False` |
   | `DJANGO_ALLOWED_HOSTS` | leave as a placeholder for now, e.g. `placeholder.example.com` — fixed once you see the real assigned domain in step 5 |
   | `DATABASE_URL` | the Neon connection string from Step 1 |
   | `CORS_ALLOWED_ORIGINS` | placeholder for now, e.g. `https://placeholder.vercel.app` — fixed in Step 4 |
   | `FRONTEND_BASE_URL` | same placeholder as above for now |
   | `EMAIL_BACKEND` | `django.core.mail.backends.console.EmailBackend` to start (emails show up in Back4app's logs — see "Real email" below) |
   | `DEFAULT_FROM_EMAIL` | e.g. `no-reply@yourdomain.com` |
   | `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` | your real Razorpay keys, or the test placeholders from `.env.example` if not accepting real payments yet |
   | `RAZORPAY_PRO_MONTHLY_PLAN_ID` | leave blank until you create a real Plan in Razorpay |
   | `GOOGLE_OAUTH_CLIENT_ID` | leave blank to keep Google Sign-In hidden, or set it if configured |
   | `SENTRY_DSN` | optional, leave blank to skip |

4. Click **Create App**. Watch the build/deploy logs.
5. Once live, note the backend's assigned URL from the dashboard, then go
   back and set `DJANGO_ALLOWED_HOSTS` to that exact hostname (no
   `https://`, just the domain), and redeploy if it doesn't happen
   automatically on saving env vars.

## Step 3 — Create the frontend project on Vercel

1. [vercel.com](https://vercel.com) → **Add New** → **Project** → **Import
   Git Repository**. First time only: **Adjust GitHub App Permissions** →
   grant access to **Only select repositories** → pick this repo.
2. **Root Directory**: `frontend` (click "Edit" next to Root Directory —
   Vercel needs this since the repo isn't frontend-only).
3. **Framework Preset**: Vite (auto-detects from `package.json`).
4. Build/output settings can stay at Vercel's Vite defaults.
5. Environment Variables:

   | Key | Value |
   |---|---|
   | `VITE_API_BASE_URL` | `https://<your-backend-domain>/api` (from Step 2) |
   | `VITE_GOOGLE_CLIENT_ID` | leave blank unless configured |
   | `VITE_PRO_PLAN_PRICE_DISPLAY` | e.g. `₹299/month` |
   | `VITE_SENTRY_DSN` | optional |

6. Click **Deploy**. Once live, note its URL: `https://<your-project>.vercel.app`.

## Step 4 — Wire the two together

Go back to the **Back4app** app → Environment variables, and update:

- `CORS_ALLOWED_ORIGINS` → `https://<your-project>.vercel.app`
- `FRONTEND_BASE_URL` → `https://<your-project>.vercel.app`

Save and redeploy if it doesn't happen automatically.

Note: every push to your default branch redeploys on Vercel, and Vercel also
spins up a unique preview URL per branch/PR by default. Preview URLs won't
be in `CORS_ALLOWED_ORIGINS`, so API calls from a preview deploy will fail
CORS until you either add that URL too or disable preview deployments
(Settings → Git) if you don't need them.

## Step 5 — Verify

1. Open the frontend URL, register a new account, log in.
2. Check the backend's logs on Back4app to confirm requests are landing and
   there are no CORS/500 errors.
3. Since `EMAIL_BACKEND` is still the console backend, password-reset and
   invoice emails will show up as text in the backend's logs, not in an
   actual inbox — see "Real email" below to fix that.

## Known limitations on Back4app's free tier

- **Resource caps**: 256MB RAM, 0.25 vCPU, 100GB transfer/month. Fine for a
  personal beta; watch memory usage since this backend also generates PDFs
  (reportlab/pillow) which is more memory-hungry than a plain API request.
- **Ephemeral disk**: generated invoice PDFs (`Invoice.pdf_file`, saved
  under `MEDIA_ROOT`) live on local disk inside the container, wiped on
  every redeploy/restart. They're regenerable — `POST
  /api/invoices/{id}/regenerate-pdf/` recreates one — but there's no
  persistence between deploys today. If this matters, swap `MEDIA` storage
  to something like Cloudinary's free tier (10GB), not wired up yet.
- **Neon autosuspend** — see Step 1; a short wake-up delay after idle
  periods, not a hard limit.
- Whether the free plan has its own inactivity spin-down (like Render's 15
  min or Koyeb's 1 hour) wasn't confirmed in Back4app's docs — note what you
  actually observe here once it's running for a while.

## Optional follow-ups

- **Real email**: switch `EMAIL_BACKEND` to
  `django.core.mail.backends.smtp.EmailBackend` and set `EMAIL_HOST` /
  `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` using a free Brevo or Resend SMTP
  relay - see the walkthrough already in `backend/.env.example`.
- **Custom domain**: check Back4app's app settings for a custom domain
  option; Vercel definitely supports one free (Project → Settings →
  Domains). Once added, update `DJANGO_ALLOWED_HOSTS`,
  `CORS_ALLOWED_ORIGINS`, and `FRONTEND_BASE_URL` to match.
- **Razorpay webhook URL**: once live, set the webhook URL in the Razorpay
  Dashboard to `https://<your-backend-domain>/api/webhooks/razorpay/`.
- **Superuser / Django admin**: if Back4app doesn't offer a shell/console on
  the free tier, the workaround is the same as before: temporarily point
  your local `.env`'s `DATABASE_URL` at the same Neon connection string, run
  `python manage.py createsuperuser` locally, then switch back.
- **Portable elsewhere**: since this is now a plain Dockerfile, the exact
  same image also runs on Google Cloud Run (real, durable always-free
  quota - 2M requests/month - but needs a credit card on file for identity
  verification even though it won't charge under quota) if Back4app's free
  tier ever changes too.
