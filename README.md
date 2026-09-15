# Event Registration & Management System

A full-stack event operations platform built for Nowshera Events Co. It centralizes event discovery, registration requests, attendee operations, approvals, reporting, and capacity management for attendees and administrators.

> The application is deployed, tested, and ready for production use.

**🌐 [Live Demo](https://event-registration-management-syste-eight.vercel.app)**<br>
**💻 [GitHub Repository](https://github.com/SHAHZAIBSAJJADAHMADKHAN/event-registration-management-system)**

## Project Overview

Nowshera Events Co. needed a structured alternative to managing events, registrations, attendee information, and operational updates across fragmented messaging and spreadsheets. This application provides one centralized platform: attendees can discover and request access to events, while administrators can manage the full event lifecycle, registration decisions, capacity, notifications, and reports.

## Key Features

### Attendee Experience

- Secure signup, sign-in, sign-out, and protected routes
- Supported email-provider validation for signup
- Browse published and upcoming events with remaining capacity
- View event details and submit registration requests
- Review personal registrations and cancel eligible registrations
- Receive persistent notifications about registration activity

### Administrator Operations

- Secure, role-protected administrator access and dashboard metrics
- Create, edit, publish, complete, cancel, and permanently delete events where supported
- Review pending registration requests and approve or reject them
- View event attendees with search and status filtering
- Manage operational capacity and check-in-friendly attendee views
- Deliver registration-status notification workflows

### Reporting and Export

- Event-level operational reporting and summary CSV export
- Detailed per-event attendee reports
- Registration-status filters: All, Approved, Pending, Rejected, and Cancelled
- Filter-aware CSV and PDF exports

## Registration Workflow

```text
Attendee
   ↓
Registration Request
   ↓
Pending
   ↓
Admin Review
   ↓
Approved / Rejected
```

- Pending requests do not reserve event capacity.
- Approved registrations consume capacity.
- An eligible cancellation restores capacity.

## Technology Stack

| Area | Technologies |
| --- | --- |
| Frontend | React, Vite, JavaScript |
| Backend | Python, FastAPI |
| Database and authentication | Supabase, PostgreSQL, Supabase Auth |
| Security | JWT authentication, server-side authorization, role-based access control, ownership checks |
| Deployment | Vercel |
| Development | Git, GitHub |
| Testing | Vitest, Testing Library, pytest |

## Architecture

```text
React Frontend
      ↓
FastAPI REST API
      ↓
Supabase / PostgreSQL
      ↓
Authentication + Application Data
```

React/Vite uses Supabase Auth for browser sessions and sends the user JWT to FastAPI. The backend verifies JWT signatures and issuer details, resolves the authoritative role from the `profiles` table, and enforces role and ownership decisions server-side. Supabase PostgreSQL stores events, profiles, registrations, and notifications; application and database rules protect capacity and duplicate registrations.

## Security

- Supabase Auth manages browser authentication sessions.
- FastAPI verifies JWTs before serving authenticated data.
- Roles and administrator access are enforced on the server, not only in the interface.
- Registration ownership checks prevent attendees from accessing another attendee's data.
- Backend-only credentials remain server-side; no secrets are stored in this repository.
- Browser-facing configuration uses only safe `VITE_*` variables. Backend secrets must never use that prefix.

## Live Demo

The deployed production application is available at:

**[https://event-registration-management-syste-eight.vercel.app](https://event-registration-management-syste-eight.vercel.app)**

Visitors can explore the deployed application without running it locally. Private test credentials and passwords are intentionally not included.

## Local Development

### 1. Clone the repository

```powershell
git clone https://github.com/SHAHZAIBSAJJADAHMADKHAN/event-registration-management-system.git
cd event-registration-management-system
```

### 2. Configure and start the backend

From `backend/`, create an ignored `.env` file from `.env.example`, create a Python virtual environment, and install dependencies.

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -3.12 -m pip install -r requirements-dev.txt
py -3.12 -m uvicorn app.main:app --reload --port 8001
```

The local API health endpoint is `http://localhost:8001/api/health`.

### 3. Configure and start the frontend

From `frontend/`, create an ignored `.env` file from `.env.example`. Configure the frontend API base URL for the backend's `/api` endpoint on port `8001`, then run:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, normally `http://localhost:5173`.

## Environment Variables

Create local `.env` files from the provided `.env.example` files. Use placeholder values only and never commit those files.

| Scope | Variable names |
| --- | --- |
| Backend | `ENVIRONMENT`, `FRONTEND_ORIGIN`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY`, `SUPABASE_JWT_ISSUER`, `SUPABASE_JWKS_URL` |
| Frontend | `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY`, `VITE_API_BASE_URL` |

`SUPABASE_SECRET_KEY` is backend-only. Never expose it, use it in a `VITE_*` variable, or commit it to the repository.

## Testing

The project includes automated frontend and backend tests and has also undergone manual production verification.

```powershell
# frontend/
npm test
npm run build

# backend/
py -3.12 -m pytest -q
```

## Deployment

The application is deployed to Vercel and uses Supabase for database and authentication services.

**Production:** [https://event-registration-management-syste-eight.vercel.app](https://event-registration-management-syste-eight.vercel.app)

Production browser requests use the application API path while FastAPI retains server-side JWT verification and authorization. Service-scoped SPA fallback supports direct refreshes of attendee and administrator routes.

## Project Documentation

- [Requirements](docs/requirements.md)
- [Architecture](docs/architecture.md)
- [Requirements traceability](docs/requirements-traceability.md)
- [Database schema](docs/database-schema.md)
- [Authentication security](docs/auth-security.md)
- [Admin event management](docs/admin-event-management.md)
- [Registration lifecycle](docs/registration-lifecycle.md)
- [Admin operations](docs/admin-operations.md)
- [Deployment and handover](docs/deployment.md)

## Author

**Shahzaib Sajjad Ahmad Khan**<br>
BS Software Engineering Student<br>
AI Automation & Full-Stack Development

GitHub: [github.com/SHAHZAIBSAJJADAHMADKHAN](https://github.com/SHAHZAIBSAJJADAHMADKHAN)
