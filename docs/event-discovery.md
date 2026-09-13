# Attendee Event Discovery API

## Scope

Phase 5 provides backend-only discovery of events available to authenticated attendees. It does not create registrations, cancel registrations, expose personal registration history, or provide frontend pages.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | /events | List published future events, nearest first |
| GET | /events/{event_id} | Retrieve one published future event |

Both endpoints require the backend attendee guard. Unauthenticated users receive HTTP 401 and non-attendee roles receive HTTP 403.

## Visibility rules

An event is discoverable only when both conditions hold:

- status is published
- starts_at is later than the current UTC time

Draft, cancelled, completed, and past published events are excluded from both list and detail responses. A hidden or missing detail returns the same safe 404 response.

## Availability

Responses include capacity, active_registration_count, and remaining_availability.

Only registrations with active status count as used capacity. Cancelled registrations remain in the database but do not reduce availability. Remaining availability is clamped at zero as a defense-in-depth response safeguard.

## Data boundary

Discovery responses intentionally omit created_by and administrative timestamps. The backend uses its server-side repository to calculate availability; frontend filtering is not an authorization boundary.
