# Database Schema — Phase 1 Foundation

The complete schema is version-controlled in supabase/migrations/20260912000100_event_management_foundation.sql. Apply it through the Supabase CLI or migration runner; no dashboard-only setup is required.

## Entity relationships

    auth.users
        │ 1:1
        ▼
    profiles ────────< events
        │                 │
        │                 │ 1:many
        └────< registrations >────┘

- profiles.id is both the primary key and a foreign key to auth.users.id.
- events.created_by references the admin profile that created the event.
- registrations.attendee_id references a profile; registrations.event_id references an event.

## Tables

### profiles

| Column | Type | Rules |
| --- | --- | --- |
| id | uuid | Primary key; references auth.users(id) with cascade deletion |
| full_name | text | Required after trimming; 1–200 characters |
| role | user_role | Required; admin or attendee; defaults to attendee |
| created_at | timestamptz | Required; defaults to now() |
| updated_at | timestamptz | Required; defaults to now() and is trigger-maintained |

An auth.users insert creates the profile automatically. The trigger always inserts attendee, even if user metadata contains a role-like value.

### events

| Column | Type | Rules |
| --- | --- | --- |
| id | uuid | Primary key; generated with gen_random_uuid() |
| title | text | Required after trimming; 1–200 characters |
| description | text | Required after trimming; 1–10,000 characters |
| starts_at | timestamptz | Required UTC-aware event start instant |
| location | text | Required after trimming; 1–300 characters |
| capacity | integer | Required and greater than zero |
| status | event_status | Required; draft, published, completed, or cancelled; defaults to draft |
| created_by | uuid | Required; references profiles(id) and must be an admin profile |
| created_at / updated_at | timestamptz | Required; automatic defaults and update trigger |

Indexes: events_discovery_idx supports future upcoming-published-event discovery.

### registrations

| Column | Type | Rules |
| --- | --- | --- |
| id | uuid | Primary key; generated with gen_random_uuid() |
| attendee_id | uuid | Required; references profiles(id) |
| event_id | uuid | Required; references events(id) |
| status | registration_status | Required; active or cancelled; defaults to active |
| created_at / updated_at | timestamptz | Required; automatic defaults and update trigger |

Indexes: registrations_event_active_idx supports active-capacity counting, and registrations_attendee_idx supports a future personal-registration view. The partial unique index registrations_one_active_per_attendee_event_idx allows only one active registration for an attendee/event pair while preserving cancelled history and allowing a later active re-registration.

## Integrity and timestamps

- PostgreSQL enums restrict valid role, event-status, and registration-status values.
- Foreign keys preserve valid identity, creator, event, and registration relationships.
- set_updated_at() updates all application-record updated_at values automatically.
- events_prevent_capacity_below_active_registrations rejects a capacity reduction below the count of active registrations.
- events_require_admin_creator prevents an attendee profile from being recorded as an event creator.

## RLS and security approach

RLS is enabled for all public application tables.

| Table | Policy | Reason |
| --- | --- | --- |
| profiles | Authenticated user selects/updates only their own row | Protect attendee identity data; a trigger blocks self-role escalation. |
| events | Anonymous and authenticated users select only published rows | Enables public discovery without exposing draft/completed/cancelled operational data. |
| registrations | Authenticated user selects only registrations whose attendee ID matches auth.uid() | Prevents attendee-to-attendee private-data access. |

There are no public insert, delete, or management policies. The backend will use server credentials only after FastAPI validates the requester and applies the required business authorization. This provides defense in depth without treating RLS as the sole business layer.

## Admin provisioning

Public sign-up always creates an attendee profile. provision_admin(profile_id) is a security definer function callable only by Supabase's service_role; it is intended for a trusted, audited backend administration process. FastAPI now resolves roles from this profile table after JWT verification, rather than trusting any client-provided role claim. There is no public role-selection field, policy, or endpoint.

## Timezone strategy

events.starts_at stores a PostgreSQL timestamptz, representing an unambiguous instant and normalized by PostgreSQL. Future event-management APIs will accept ISO 8601 timestamps with an explicit UTC offset or IANA-zone-aware conversion at the service boundary. React will display the event in the chosen event/local timezone, while all eligibility comparisons use PostgreSQL now() against starts_at.

## Concurrent capacity strategy

create_registration_atomic(event_id, attendee_id) is server-only and intentionally has no public API route in Phase 1. It locks the selected event row with FOR UPDATE, verifies that the event is published and in the future, detects existing active registration, counts active registrations, verifies capacity, and inserts one active record within one transaction. The partial unique index provides an additional duplicate-registration guard. A later FastAPI registration service must first verify the caller JWT and pass its subject as attendee_id through a Supabase secret-key client; it must not expose secret credentials or this RPC directly to the browser.

## Deferred work

Phase 7 adds backend-only admin operations without a schema change: the existing event/registration relationships support attendee lists, active-only capacity totals, check-in data, and CSV export. See [Admin attendee operations API](admin-operations.md). Frontend work remains deferred.
