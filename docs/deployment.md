# Deployment and Handover

This project is prepared for the following production flow:

```text
Vercel React/Vite frontend → Render FastAPI backend → Supabase Auth and PostgreSQL
```

Actual cloud deployment is pending. Do not use placeholder values as credentials.

## Render backend

Create a **Web Service** from this repository.

- Root directory: `backend`
- Runtime: Python 3.12
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check: `/health`

Set these private environment-variable names in Render:

- `ENVIRONMENT=production`
- `FRONTEND_ORIGIN` — the exact Vercel production origin; multiple origins may be comma-separated through `FRONTEND_ORIGINS`
- `SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEY`
- `SUPABASE_SECRET_KEY`
- `SUPABASE_JWT_ISSUER`
- `SUPABASE_JWKS_URL`

`SUPABASE_SECRET_KEY` stays in Render only. Never add it to Vercel or the repository. The health endpoint returns only a service status and contains no database or configuration details.

## Vercel frontend

Import the same repository as a Vercel project.

- Root directory: `frontend`
- Framework preset: Vite
- Build command: `npm ci && npm run build`
- Output directory: `dist`

Set only browser-safe variables:

- `VITE_API_BASE_URL` — the public HTTPS Render backend URL
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_PUBLISHABLE_KEY`

`vercel.json` rewrites client-side routes to `index.html`, allowing direct refreshes of attendee and admin URLs without replacing static-asset handling.

## Supabase production checklist

After the Vercel URL exists:

1. Set Supabase Auth **Site URL** to the production frontend URL.
2. Add the production frontend URL and required local development URL to **Redirect URLs**.
3. Confirm Vercel has no backend secret variables.
4. Keep existing RLS policies and FastAPI authorization enabled.
5. Confirm Render `FRONTEND_ORIGIN` exactly matches the Vercel origin.

## Post-deployment smoke test

1. Request `GET /health` from the Render URL.
2. Open a direct client route such as `/events` and an admin route such as `/admin/dashboard`.
3. Sign in as an attendee and an admin using separately managed test credentials.
4. Confirm authenticated API calls, CORS, role authorization, registration ownership, reports, and CSV export.

## Handover checklist

- Live frontend URL: pending deployment
- Live backend URL: pending deployment
- GitHub repository: provide the repository URL at handover
- Architecture: [architecture.md](architecture.md)
- Database evidence: [database-schema.md](database-schema.md)
- Feature traceability: [requirements-traceability.md](requirements-traceability.md)
- Test evidence: backend pytest and frontend Vitest/build commands in the README
- Screenshots: capture landing, attendee events, registration, admin events, attendee list, dashboard, and reports after deployment

Do not store test credentials in this repository. Share them through a separate secure channel only.
