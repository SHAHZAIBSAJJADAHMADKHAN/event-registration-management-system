# Architecture

## System flow

```text
React Frontend
      |
      v
FastAPI REST API
      |
      v
Business / Service Layer
      |
      v
Supabase PostgreSQL
```

Supabase Auth issues authenticated-user JWTs. The React application will attach the current token to protected API calls. FastAPI will validate the JWT and perform role and ownership checks before allowing protected work. The frontend may adapt its navigation to a user's role, but it is never the authorization boundary.

## Phase 1 implementation

- `supabase/migrations/20260912000100_event_management_foundation.sql` reproducibly creates application tables, status enums, constraints, indexes, timestamp triggers, RLS policies, and server-only database functions.
- `backend/app/` provides FastAPI application configuration, constrained CORS, safe error primitives, a Supabase client factory, foundational validation schemas, and only `/` and `/health` system endpoints.
- No authentication, event management, registration, cancellation, report, or dashboard feature routes are exposed in this phase.

## Phase 2 verification

- The Phase 1 migration has been applied to the development database and verified through backend integration tests using the configured Supabase publishable and secret keys.
- The opt-in test suite verifies table access, enum/check/foreign-key rules, the active-registration unique index, the capacity-reduction trigger, the server-only RPCs, and RLS data isolation.
- This verification adds no product endpoints and does not implement JWT request authorization.

## Phase 3 authentication and authorization

- FastAPI now verifies Supabase Bearer JWT signatures against the configured JWKS, enforces the configured issuer and expiration, and rejects malformed or invalid tokens.
- The backend resolves the authenticated subject to the authoritative `profiles` row; role claims supplied in a JWT are not trusted for authorization.
- Reusable authentication, admin, attendee, and attendee-ownership dependencies enforce backend authorization. `GET /auth/me` is the sole Phase 3 identity endpoint and returns only the authenticated user's profile data.
- Self-service users remain attendees. Admin role assignment is restricted to the existing server-only database provisioning function.

## Phase 4 admin event management

- FastAPI exposes admin-only event create, list, detail, update, and status-transition endpoints backed by an event repository and business service.
- Event detail updates exclude status changes; the lifecycle endpoint permits only draft to published/cancelled and published to completed/cancelled transitions.
- Event history is preserved by omitting hard deletion. The existing database capacity trigger remains the final data-integrity defense, alongside a service-level active-registration precheck.

## Phase 5 attendee event discovery

- Attendee-only list and detail endpoints return only Published events with a future `starts_at` timestamp, ordered nearest first.
- Discovery responses calculate active registrations and remaining availability server-side. Cancelled registrations do not consume capacity, and administrative creator/timestamp fields are not exposed.
- The phase does not create, cancel, or list attendee registrations.

## Phase 6 attendee registration lifecycle

- Attendee-only registration creation delegates to the existing database atomic RPC, preserving event-row locking and capacity integrity.
- Personal list/detail/cancel endpoints scope every registration query and update to the authenticated attendee; cross-attendee resources receive safe not-found responses.
- Cancellation preserves history by changing status to cancelled. Discovery availability immediately reflects the active-only registration count.

## Phase 7 admin attendee operations and reports

- Admin-only attendee-list, dashboard, operational-summary, check-in, and CSV-export endpoints use the same FastAPI admin dependency as event management.
- The backend retrieves profile names from the application table and email only through its trusted Supabase admin client after authorization. Attendees cannot access operational lists, totals, reports, or exports.
- Dashboard and event-summary capacity calculations count active registrations only; cancelled history remains visible without consuming availability.

## Phase 8 frontend authentication foundation

- React/Vite owns browser-safe Supabase Auth session lifecycle only, using the public URL and publishable key from `frontend/.env`.
- The browser sends its current access token to FastAPI's `/auth/me` endpoint, which validates the JWT and resolves the database-backed role before the frontend selects an application area.
- Frontend protected routes prevent content flashes and improve navigation, but FastAPI guards and database RLS remain the authorization boundary.

## Layer responsibilities

### React frontend

- Provide responsive, accessible pages for public, attendee, and administrator journeys.
- Manage client-side form state, loading, empty, success, and error states.
- Call the REST API and render API-provided data without holding privileged secrets.
- Present role-appropriate navigation for usability while relying on FastAPI for enforcement.

### FastAPI REST API

- Expose root, health, and authenticated current-user identity endpoints; later expose versioned product endpoints.
- Parse and validate request data with Pydantic schemas.
- Validate Supabase JWTs, identify the caller, load the authoritative profile role, and provide reusable Admin, Attendee, and ownership enforcement dependencies.
- Return meaningful HTTP status codes and consistent error responses.

### Business / service layer

- Centralize business rules so they are not duplicated across route handlers.
- Evaluate event eligibility, status transitions, registration uniqueness, capacity protection, cancellation effects, and dashboard calculations.
- Coordinate database operations transactionally where required to keep capacity and registration state accurate.

### Supabase PostgreSQL

- Persist users/roles, events, registrations, timestamps, and their relationships.
- Apply database constraints needed for durable integrity, including uniqueness and capacity-related safeguards designed in the database phase.
- Serve as the durable source for attendee lists, availability, and dashboard/report calculations.

## Authentication and configuration boundary

- Supabase Auth is the identity provider.
- FastAPI verifies JWTs with the configured issuer and JWKS endpoint; login and signup user interfaces remain deferred.
- Public Supabase URL and publishable key may be provided to the frontend through build-time environment variables; Supabase secret keys stay exclusively in backend environment configuration.
- See [database schema](database-schema.md) for the implemented schema, RLS, role-provisioning, timestamp, concurrency, and timezone decisions.
- Specific feature schemas/endpoints, deployment target, and full authentication implementation are deferred to later phases.
