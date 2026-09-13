# Vercel Deployment Preparation

This repository is prepared for one Vercel **Services** deployment: a Vite frontend at `/` and a native FastAPI service exposed at `/api`. No deployment has been performed by this repository.

## Repository routing

The root [`vercel.json`](../vercel.json) defines two services:

- `frontend` uses `frontend/`, Vite, `npm run build`, and `dist` output.
- `backend` uses `backend/` and the native FastAPI entry point `app.main:app`.

Top-level routing sends `/api/*` requests to the FastAPI service before sending all remaining traffic to the frontend service. A backend service route captures the suffix as `apiPath` and applies the native Vercel `request.path` transform to `/api/<path>` before FastAPI sees it. As a result, `/api/health` reaches the existing `/health` route and `/api/auth/me` reaches `/auth/me`, without changing application routes.

The frontend service has its own SPA fallback to `index.html`. Direct refreshes of attendee and admin routes, including `/events`, `/my-registrations`, `/admin`, `/admin/events`, and `/admin/reports`, remain frontend requests. API paths are selected first and never fall through to the SPA.

## Vercel project setup

1. Import the repository as one Vercel project.
2. In **Build and Deployment**, choose the **Services** framework setting. Vercel Services is required because the project contains the Vite and FastAPI services.
3. Keep the repository root as the project root; do not set it to `frontend` or `backend`.
4. Let `vercel.json` define the two service roots and native FastAPI entry point. Do not configure an `uvicorn` start command on Vercel.
5. Add the environment variables below to the required Vercel environments before deploying.

## Environment variables

Set these backend-only values in Vercel. They are read by FastAPI and must never use a `VITE_` prefix:

- `ENVIRONMENT=production`
- `FRONTEND_ORIGIN=https://<your-production-domain>`
- `SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEY`
- `SUPABASE_SECRET_KEY`
- `SUPABASE_JWT_ISSUER`
- `SUPABASE_JWKS_URL`

Set these browser-safe frontend build values in Vercel:

- `VITE_API_BASE_URL=/api`
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_PUBLISHABLE_KEY`

`VITE_API_BASE_URL=/api` keeps browser-to-API requests on the deployment origin. This avoids cross-origin browser requests while the backend retains its existing server-side JWT verification and authorization behavior. Never expose `SUPABASE_SECRET_KEY` to the frontend service or in a `VITE_*` variable.

For local development, set ignored `frontend/.env` to `VITE_API_BASE_URL=http://localhost:8000`. The example file intentionally shows the production-safe `/api` value.

## Supabase production checklist

After Vercel supplies the production domain:

1. Set Supabase Auth **Site URL** to the exact production frontend URL.
2. Add the production frontend URL and required local development URL to Supabase Auth **Redirect URLs**.
3. Set `FRONTEND_ORIGIN` to the exact production domain. Multiple explicit origins can be supplied through `FRONTEND_ORIGINS` when required.
4. Confirm `SUPABASE_SECRET_KEY` exists only in backend runtime configuration.
5. Keep the existing Supabase RLS policies and FastAPI authorization enabled.

## Post-deployment smoke test

1. Request `GET /api/health` from the Vercel deployment.
2. Directly open `/events` and `/admin/dashboard` to verify SPA refresh behavior.
3. Sign in as an attendee and an admin using separately managed credentials.
4. Confirm authenticated `/api` requests, role authorization, registration ownership, reports, and CSV export.

Do not store deployment credentials or test-account credentials in this repository.
