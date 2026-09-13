# Frontend Authentication Foundation

Phase 8 provides the React/Vite JavaScript shell, public landing page, attendee-only signup, sign-in, sign-out, session restoration, API client, and role-aware route guards.

## Configuration

Copy `frontend/.env.example` to a local ignored `frontend/.env` and set only:

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_PUBLISHABLE_KEY`
- `VITE_API_BASE_URL`

The browser client never receives the Supabase secret key, service-role credential, database password, or CLI token.

## Authentication and roles

The browser uses Supabase Auth for signup, sign-in, session persistence, refresh, and sign-out. Sign-up sends only a name, email, and password. It has no role selector; the existing database trigger creates self-service accounts as attendees.

After a session is present, the app calls FastAPI `GET /auth/me` with the current Supabase access token. That server-verified profile is used for navigation only. FastAPI remains the authority for all protected data and operations.

`ProtectedRoute` prevents protected content from rendering during session/profile loading, redirects unauthenticated visitors to sign-in, and directs users with the wrong role to their own area. These guards are UX controls, not authorization controls.

## Current routes

| Route | Access | Current scope |
| --- | --- | --- |
| `/` | Public | Landing page |
| `/sign-up` | Public | Attendee-only account registration |
| `/sign-in` | Public | Sign in |
| `/events`, `/my-registrations` | Attendee | Protected placeholders |
| `/admin/dashboard`, `/admin/events`, `/admin/reports` | Admin | Protected placeholders |

Event, registration, dashboard, and report content is deliberately deferred to later frontend phases.
