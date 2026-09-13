# Attendee Registration Lifecycle API

## Scope

Phase 6 provides backend-only registration creation, cancellation, and personal-registration history. It does not include frontend pages, payment, email, attendee check-in, or administrative attendee-list features.

## Endpoints

All endpoints require a valid Supabase JWT and the backend attendee role guard.

| Method | Path | Purpose |
| --- | --- | --- |
| POST | /events/{event_id}/registrations | Atomically register the current attendee |
| GET | /me/registrations | List only the current attendee's registrations |
| GET | /me/registrations/{registration_id} | Read one owned registration |
| PATCH | /me/registrations/{registration_id}/cancel | Cancel one owned active registration |

## Atomic registration

Creation calls the existing server-only create_registration_atomic database RPC. That function locks the event row, verifies published/future eligibility, checks duplicate active registration and capacity, then inserts the registration in one transaction.

The API maps safe outcomes to not-found or conflict responses without exposing database internals.

## Cancellation and ownership

Cancellation updates the owned registration from active to cancelled; it never deletes the record. The update is scoped to both registration ID and authenticated attendee ID. Other attendees receive the same safe not-found response as for an unknown registration.

A second cancellation receives a conflict response. Because only active rows consume capacity, cancellation immediately releases availability for discovery and later registration attempts.

## My Registrations response

Personal registration responses contain registration ID/status/timestamps and event ID, title, schedule, location, and status. They do not expose another attendee's data or administrative event fields.

## Capacity and history

The database partial unique index still permits at most one active registration per attendee/event while keeping cancelled history. The discovery service counts only active rows, so remaining availability never includes cancelled registrations as used capacity.
