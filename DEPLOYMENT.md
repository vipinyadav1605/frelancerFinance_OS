# Deploying to Render

Two services + one database, all on Render:

- **Backend** — a Web Service (Python/Django + gunicorn)
- **Frontend** — a Static Site (Vite build output)
- **Database** — a managed Postgres instance

Render can't be driven from here (it needs your login), so this is a guide
to follow in Render's dashboard. Everything on the repo side is already
prepped — see "What's already done" below.

## What's already done in this repo

- `backend/build.sh` — Render's build step: install deps, `collectstatic`, `migrate`.
- `whitenoise` added so Django serves its own admin static files with no
  separate static host needed.
- `config/settings.py`: `SECURE_PROXY_SSL_HEADER` uncommented (Render's proxy
  sets `X-Forwarded-Proto`, confirming HTTPS was actually used) - this only
  activates when `DJANGO_DEBUG=False`.
- `frontend/public/_redirects` — `/* /index.html 200`, so refreshing a
  client-side route (e.g. `/dashboard`) doesn't 404 on a static host.
- `gunicorn` was already in `requirements.txt` from earlier.

**Before you start**: commit and push these files (`build.sh`, `_redirects`,
the `settings.py`/`requirements.txt` changes) — Render builds from your
GitHub repo, so nothing here takes effect until it's pushed.

```
git add backend/build.sh backend/config/settings.py backend/requirements.txt frontend/public/_redirects
git commit -m "Prep for Render deployment"
git push
```

## Step 1 — Create the Postgres database

1. Render dashboard → **New** → **PostgreSQL**.
2. Name: `freelancer-finance-os-db`. Region: pick one close to you (e.g.
   Singapore). Plan: **Free** to start.
3. Once created, open it and copy the **Internal Database URL** (starts with
   `postgres://...`) — you'll paste this into the backend service next.
   Use the *Internal* URL, not the External one - internal traffic between
   Render services in the same region is free and faster.
4. **Know the limits before you commit to this**: Render's free Postgres
   plan is time-limited (it expires after a set trial period and then needs
   upgrading to a paid plan to keep the data) - check the current terms on
   Render's pricing page before relying on it long-term. If that matters for
   this project, budget for their cheapest paid Postgres tier instead from
   the start.

## Step 2 — Create the backend web service

1. Render dashboard → **New** → **Web Service** → connect your GitHub repo
   (`frelancerFinance_OS`).
2. **Root Directory**: `backend`
3. **Runtime**: Python 3
4. **Build Command**: `bash build.sh`
5. **Start Command**: `gunicorn config.wsgi:application`
6. **Plan**: Free to start (see cold-start note below).
7. Environment variables (Settings → Environment) — set all of these:

   | Key | Value |
   |---|---|
   | `DJANGO_SECRET_KEY` | generate one: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
   | `DJANGO_DEBUG` | `False` |
   | `DJANGO_ALLOWED_HOSTS` | `<your-backend-name>.onrender.com` (shown once the service is created) |
   | `DATABASE_URL` | the Internal Database URL from Step 1 |
   | `CORS_ALLOWED_ORIGINS` | placeholder for now, e.g. `https://placeholder.onrender.com` — you'll fix this in Step 4 |
   | `FRONTEND_BASE_URL` | same placeholder as above for now |
   | `EMAIL_BACKEND` | `django.core.mail.backends.console.EmailBackend` to start (emails just show up in Render's logs — see "Real email" below to actually send them) |
   | `DEFAULT_FROM_EMAIL` | e.g. `no-reply@yourdomain.com` |
   | `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` | your real Razorpay keys, or leave the test placeholders from `.env.example` if you're not accepting real payments yet |
   | `RAZORPAY_PRO_MONTHLY_PLAN_ID` | leave blank until you create a real Plan in Razorpay |
   | `GOOGLE_OAUTH_CLIENT_ID` | leave blank to keep Google Sign-In hidden, or set it if configured |
   | `SENTRY_DSN` | optional, leave blank to skip |
   | `PYTHON_VERSION` | `3.12.7` (pins the Python version to match local dev) |

8. Click **Create Web Service**. Watch the build logs — `build.sh` will
   install everything, collect static files, and run migrations against the
   database from Step 1.
9. Once live, note the backend's URL: `https://<your-backend-name>.onrender.com`.

## Step 3 — Create the frontend static site

1. Render dashboard → **New** → **Static Site** → same GitHub repo.
2. **Root Directory**: `frontend`
3. **Build Command**: `npm install && npm run build`
4. **Publish Directory**: `dist`
5. Environment variables:

   | Key | Value |
   |---|---|
   | `VITE_API_BASE_URL` | `https://<your-backend-name>.onrender.com/api` (from Step 2) |
   | `VITE_GOOGLE_CLIENT_ID` | leave blank unless configured |
   | `VITE_PRO_PLAN_PRICE_DISPLAY` | e.g. `₹299/month` |
   | `VITE_SENTRY_DSN` | optional |
   | `NODE_VERSION` | `20` |

6. Click **Create Static Site**. Once live, note its URL:
   `https://<your-frontend-name>.onrender.com`.

## Step 4 — Wire the two together

Go back to the **backend** service → Environment, and update:

- `CORS_ALLOWED_ORIGINS` → `https://<your-frontend-name>.onrender.com`
- `FRONTEND_BASE_URL` → `https://<your-frontend-name>.onrender.com`

Save - this triggers an automatic redeploy of the backend. Once it's back
up, the two services are fully connected.

## Step 5 — Verify

1. Open the frontend URL, register a new account, log in.
2. Check the backend's **Logs** tab in Render to confirm requests are
   landing and there are no CORS/500 errors.
3. Since `EMAIL_BACKEND` is still the console backend, password-reset and
   invoice emails will show up as text in the backend's logs, not in an
   actual inbox — see "Real email" below to fix that.

## Known limitations on Render's free tier

- **Cold starts**: a free Web Service spins down after ~15 minutes of no
  traffic and takes 30-60 seconds to wake up on the next request. Fine for a
  personal beta; upgrade to a paid plan before pointing real users at it if
  that delay matters.
- **Ephemeral disk**: generated invoice PDFs (`Invoice.pdf_file`, saved under
  `MEDIA_ROOT`) live on local disk, which Render wipes on every deploy/restart
  on the free/starter tier. They're regenerable — `POST
  /api/invoices/{id}/regenerate-pdf/` recreates one - but there's no
  persistence between deploys today. If this matters, the fix is swapping
  `MEDIA` storage to something like Cloudinary's free tier (10GB) or a small
  Render persistent disk (paid), not something wired up yet.
- **Free Postgres expiry** — see Step 1.

## Optional follow-ups

- **Real email**: switch `EMAIL_BACKEND` to
  `django.core.mail.backends.smtp.EmailBackend` and set `EMAIL_HOST` /
  `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` using a free Brevo or Resend SMTP
  relay - see the walkthrough already in `backend/.env.example`.
- **Custom domain**: Render supports free custom domains on both the Web
  Service and Static Site (Settings → Custom Domains). Once added, update
  `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, and `FRONTEND_BASE_URL` to
  match.
- **Razorpay webhook URL**: once live, set the webhook URL in the Razorpay
  Dashboard to `https://<your-backend-name>.onrender.com/api/webhooks/razorpay/`.
- **Superuser / Django admin**: Render's paid plans include a web Shell tab
  (Dashboard → your service → Shell) where you can run
  `python manage.py createsuperuser`. Not available on the free plan.
