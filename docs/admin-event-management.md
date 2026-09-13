# Admin Event Management API

## Scope

Phase 4 provides backend-only event management for authenticated administrators. It does not provide attendee discovery, registration, cancellation, reports, or frontend screens.

## Endpoints

All endpoints require a valid Supabase Bearer token and a database-backed admin role.

| Method | Path | Purpose |
| --- | --- | --- |
| POST | /admin/events | Create a draft event |
| GET | /admin/events | List all events, including every status |
| GET | /admin/events/{event_id} | Retrieve one event |
| PATCH | /admin/events/{event_id} | Update event details |
| PATCH | /admin/events/{event_id}/status | Apply an allowed lifecycle transition |

Events use a timezone-aware starts_at timestamp. Incoming schedules must include a UTC offset or timezone.

## Lifecycle

New events are created as draft. Status mutation is intentionally excluded from the general update endpoint.

| Current status | Allowed next status |
| --- | --- |
| draft | published, cancelled |
| published | completed, cancelled |
| completed | none |
| cancelled | none |

Completed and cancelled events are terminal, so they cannot become eligible for future registration.

## Validation and capacity

Title, description, location, schedule, and positive whole-number capacity are validated by Pydantic. The service blocks capacity reductions below active registration count, and the existing database trigger remains the final integrity safeguard for concurrent database operations.

## Delete behavior

There is no hard-delete endpoint. Cancellation is the operationally safe way to retire an event because it preserves event history and related registration records. A later archival policy, if required, must be designed explicitly rather than deleting operational data.

## Authorization

Every endpoint depends on require_admin. The backend verifies the JWT and loads the role from profiles; attendees receive HTTP 403 regardless of any frontend behavior.
