# Admin Attendee Operations API

## Scope

Phase 7 provides backend-only attendee management and operational reporting. Every endpoint requires a verified Supabase JWT and the server-side admin guard. There are no attendee, anonymous, or frontend exceptions.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | /admin/dashboard | System totals: events, registrations, active registrations, and available capacity |
| GET | /admin/events/{event_id}/attendees | Event registrations with attendee profile and trusted backend email data |
| GET | /admin/events/{event_id}/summary | Capacity, active/cancelled counts, and remaining availability |
| GET | /admin/events/{event_id}/check-in | Active-attendee list for practical check-in use |
| GET | /admin/events/{event_id}/attendees/export.csv | Event-specific attendee-list CSV export |

The attendee-list and CSV endpoints accept optional `status=active|cancelled` and `search=<name-or-email>` query parameters. Search is intentionally limited to attendee name and email.

## Privacy and export

Names come from `profiles`; email is retrieved only by the backend's trusted Supabase admin client after the API has passed the admin guard. No token, password, role-management, or other authentication data is returned.

The CSV uses fixed operational headers and a UUID-only filename (`event-{event_id}-attendees.csv`), avoiding event-title filename injection. Cells beginning with spreadsheet formula characters are prefixed safely before export.

## Calculations

Only registrations with `status=active` consume capacity. Remaining availability is `max(capacity - active registrations, 0)`. Dashboard available capacity sums that calculation across existing events. Cancelled registrations remain in totals/history but do not reduce available capacity.

The check-in endpoint deliberately returns active registrations only. It is a structured operational list, not QR-code or attendance-state functionality.
