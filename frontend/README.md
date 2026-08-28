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

## Pages

| Route | Purpose |
|---|---|
| `/register`, `/login` | FR-1 |
| `/forgot-password`, `/reset-password/:uid/:token` | Password reset via emailed link |
| `/business-profile` | FR-2 |
| `/clients` | FR-3: list, add, edit clients |
| `/invoices` | FR-4/FR-5: invoice list with status filters |
| `/invoices/new` | FR-4/FR-5: create invoice, tax computed server-side |
| `/invoices/:id` | FR-6: view invoice, download PDF, send, mark paid |
| `/expenses` | Phase 2: manual expense entry, CSV bank-statement import with column mapping, filter by category/date |
| `/dashboard` | Phase 3/4: P&L, GST liability, 44ADA income tax estimate, GSTR-1 pre-fill summary, CSV/PDF/GSTR-1 export - default landing page |
| `/recurring-invoices` | Phase 4: manage recurring invoice templates (weekly/monthly/quarterly, optional auto-send) |
| `/integrations` | Phase 5: manage API keys and outgoing webhook subscriptions |
| `/shared/:token` | Phase 5: public, no-login read-only report view (for a CA/collaborator) |
| `/settings` | Consolidated hub (tabs: Profile, Business, Security, Notifications, Integrations, Danger Zone) - reuses `BusinessProfilePage`/`IntegrationsPage` as tab content rather than duplicating them. `/business-profile` and `/integrations` still work standalone. |

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
