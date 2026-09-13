# Project Requirements

## Client problem

Nowshera Events Co. organizes workshops, seminars, and community events. Registrations currently arrive through WhatsApp and spreadsheets, making capacity control, confirmation, accurate attendee lists, and event-performance visibility difficult.

## Project goal

Deliver a professional, full-stack Event Registration & Management System that gives attendees a secure self-service registration journey and gives administrators dependable event operations, attendee data, and reporting.

## Roles

| Role | Responsibilities and limits |
| --- | --- |
| Admin | Authenticated users who manage events, their lifecycle, attendee lists, dashboards, and reports. They must not change attendee identity data without a valid operational reason. |
| Attendee | Authenticated users who discover published events, register when eligible, view their own registrations, and cancel eligible registrations. They cannot manage events or access other attendees' private data. |

## Required modules

1. Authentication
2. Event Management
3. Event Discovery
4. Registration
5. Attendee Management
6. Dashboard & Reports

## Functional requirements

| ID | Requirement |
| --- | --- |
| FR-01 | Users can create an account, sign in, and sign out. |
| FR-02 | The system distinguishes Admin and Attendee permissions. |
| FR-03 | The backend authorizes protected data and operations; frontend visibility alone is insufficient. |
| FR-04 | Admins can create and edit events with title, description, date, time, location, capacity, and status. |
| FR-05 | Attendee discovery displays only upcoming events with Published status. |
| FR-06 | Admins can move events through Draft, Published, Completed, and Cancelled statuses. |
| FR-07 | Authenticated attendees can register for eligible events. |
| FR-08 | The system rejects duplicate, closed, cancelled, past, and over-capacity registrations. |
| FR-09 | Attendees can view and cancel their own eligible registrations. |
| FR-10 | Registration and cancellation immediately update availability. |
| FR-11 | Admins can view attendees for a selected event. |
| FR-12 | The dashboard displays useful totals for events, registrations, and available capacity. |
| FR-13 | Admins can obtain a practical attendee list for event check-in. |

## Business rules and data integrity

- An attendee may have only one active registration for any event.
- Registration is allowed only for a future, Published event with remaining capacity.
- Cancelled registrations do not count toward used capacity.
- Only Admins can create events or transition them to Published, Completed, or Cancelled.
- Completed and Cancelled events cannot accept new registrations.
- Capacity is a positive whole number and cannot be reduced below active registration count.
- Important records retain `created_at` and `updated_at` timestamps.
- The data model must support users, roles, events, registrations, their relationships, and accurate calculations for used capacity, remaining capacity, and dashboard totals.

## Security requirements

- Authenticate users and enforce Admin/Attendee roles on the backend.
- Authorize protected operations and record ownership on every applicable request.
- Validate incoming data before persistence and return appropriate, meaningful errors.
- Do not expose Supabase secret keys or any secrets in frontend code.
- Prevent attendees from accessing another attendee's registrations or other private data.
- Store secrets in environment variables; frontend controls are never treated as authorization.

## Required pages

| Area | Page |
| --- | --- |
| Public / Auth | Account Registration; Sign In |
| Attendee | Upcoming Events; Event Details; My Registrations |
| Admin | Admin Dashboard; Event Management; Event Attendee List; Reports / Export View |

## Acceptance tests

1. **Valid registration:** An authenticated attendee registers for a future, Published event with capacity. Exactly one registration is stored, availability changes immediately, and the attendee receives clear confirmation.
2. **Duplicate registration:** An attendee with an existing active registration attempts the same event again. No duplicate active record is created and a useful explanation is returned.
3. **Capacity protection:** After capacity is reached, another attendee's registration is rejected, capacity is never exceeded, and the event is shown as full.
4. **Privacy protection:** When Attendee A requests Attendee B's registration data, the backend denies access and returns no private registration data.

## Scoring target

| Category | Points |
| --- | ---: |
| Core functionality | 35 |
| Business rules and data integrity | 20 |
| Authentication and security | 15 |
| UX, responsiveness, and accessibility | 15 |
| Code quality and testing | 10 |
| Deployment and handover | 5 |
| **Total target** | **100** |

The final handover must include a live application, test accounts, meaningful Git history, a professional README, schema diagram or screenshot, feature checklist, screenshots, known limitations, and testing evidence.

## Out of scope

- Online payments
- Seat maps or reserved seating
- Native mobile applications
- Real SMS infrastructure
- QR-code check-in
- Multi-language support
- Advanced ticket pricing
- Production-scale email delivery
