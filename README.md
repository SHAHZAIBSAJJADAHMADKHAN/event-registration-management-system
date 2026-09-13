# Event Registration & Management System

Nowshera Events Co. is a React, FastAPI, and Supabase platform for secure event discovery, registration, capacity control, attendee operations, and reporting.

## Current status

Phases 1–12 are implemented locally: authentication and role authorization, attendee event and registration workflows, admin event management, attendee check-in lists, dashboard totals, reports, and CSV export. Deployment remains intentionally out of scope.

## Architecture

React/Vite uses Supabase Auth for browser sessions and sends the user JWT to FastAPI. FastAPI verifies JWT signatures/issuer, resolves the role from the `profiles` table, and enforces role and ownership authorization server-side. Supabase PostgreSQL stores events, profiles, and registrations; atomic registration logic and database constraints protect capacity and duplicates.

## Stack

- Frontend: React, Vite, JavaScript
- Backend: FastAPI, Python
- Data/Auth: Supabase PostgreSQL and Supabase Auth
- Testing: Vitest/Testing Library and pytest

## Features

- Attendee signup/sign-in/sign-out, protected routes, event discovery, registration, cancellation, and personal registrations
- Admin event creation, editing, lifecycle transitions, attendee lists, search/filtering, check-in-friendly views, dashboard metrics, reports, and CSV export
- Backend-enforced role authorization, registration ownership, active-only capacity accounting, duplicate prevention, and lifecycle validation

## Local setup

### Backend

From `backend/`, copy `backend/.env.example` to ignored `backend/.env`, then provide local values:

```powershell
py -3.12 -m pip install -r requirements-dev.txt
py -3.12 -m uvicorn app.main:app --reload --port 8000
```

Required backend variables are `ENVIRONMENT`, `FRONTEND_ORIGIN`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY`, `SUPABASE_JWT_ISSUER`, and `SUPABASE_JWKS_URL`. `SUPABASE_SECRET_KEY` is backend-only.

### Frontend

From `frontend/`, copy `frontend/.env.example` to ignored `frontend/.env`:

```powershell
npm install
npm run dev
```

Browser-safe variables are `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY`, and `VITE_API_BASE_URL`. Never put a Supabase secret key in a `VITE_*` variable.

## Tests

```powershell
# frontend/
npm test -- --run
npm run build

# backend/
py -3.12 -m pytest -q
```

## Deployment preparation

The intended production flow is **Vercel Services (Vite + FastAPI) → Supabase**. The application is prepared for deployment but no cloud service has been deployed yet.

- Keep the Vercel project root at this repository root and select the **Services** framework setting.
- `vercel.json` declares `frontend/` as the Vite service and `backend/` as the native FastAPI service.
- Browser API requests use `VITE_API_BASE_URL=/api` in Vercel; the deployment routes that prefix to FastAPI while preserving existing backend routes.
- Vercel receives browser-safe frontend variables plus backend runtime variables, including backend-only `SUPABASE_SECRET_KEY`. Never use a `VITE_*` prefix for the secret key.
- Service-scoped SPA fallback preserves direct refreshes for client routes.

See [deployment and handover](docs/deployment.md) for the full environment-variable, Supabase redirect URL, smoke-test, test-credential, and final-delivery checklist.

## Documentation

- [Requirements](docs/requirements.md)
- [Architecture](docs/architecture.md)
- [Requirements traceability](docs/requirements-traceability.md)
- [Database schema](docs/database-schema.md)
- [Authentication security](docs/auth-security.md)
- [Admin event management](docs/admin-event-management.md)
- [Registration lifecycle](docs/registration-lifecycle.md)
- [Admin operations](docs/admin-operations.md)
