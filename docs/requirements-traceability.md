# Requirements Traceability

Phases 1–12 establish and test the schema, JWT/role security, attendee workflows, admin operations, and reporting. Statuses below reflect implemented and automated-test-covered requirements; deployment remains out of scope.

| Requirement | Feature / Module | Planned Backend Area | Planned Frontend Area | Test Required | Status |
| --- | --- | --- | --- | --- | --- |
| FR-01 | Authentication | JWT verification, profile resolution, and current-user endpoint | Attendee signup, sign-in, session restoration, and sign-out UI | Backend token tests plus frontend validation/API tests | COMPLETE |
| FR-02 | Authentication | Database-backed role resolution plus Admin/Attendee guards | Role-aware navigation and protected routes | Backend permission tests plus frontend role-route tests | COMPLETE |
| FR-03 | Authentication / Security | Server-side JWT, role, registration-ownership enforcement, and RLS defense in depth | JWT-attaching API client and UX-only route guards | Direct unauthorized/cross-attendee, API header, and protected-route tests | COMPLETE |
| FR-04 | Event Management | Admin-only create/list/detail/update API, schemas, service, repository, and capacity precheck | Event Management form and list | Admin authorization, validation, detail, update, and capacity tests | COMPLETE |
| FR-05 | Event Discovery | Attendee-only published/future list and detail API with server-side availability calculation | Upcoming Events listing | Visibility, detail, availability, and authorization tests | COMPLETE |
| FR-06 | Event Management | Admin-only guarded lifecycle transition service and endpoint | Event status controls | Valid and forbidden transition tests | COMPLETE |
| FR-07 | Registration | Attendee-only endpoint calling atomic registration RPC | Event Details registration action | Successful registration and eligibility tests | COMPLETE |
| FR-08 | Registration | Atomic RPC, partial unique index, and capacity checks with API error mapping | Registration error/full-state feedback | Duplicate, status, past-event, and full-capacity tests | COMPLETE |
| FR-09 | Registration | Owned list/detail/cancel endpoints preserving cancelled history | My Registrations page | Ownership, cancellation, and repeated-cancellation tests | COMPLETE |
| FR-10 | Registration / Availability | Active-only capacity accounting after atomic create/cancel | Availability indicators and confirmation state | Registration/cancellation availability tests | COMPLETE |
| FR-11 | Attendee Management | Admin-only per-event registration list with active/cancelled filtering and trusted name/email lookup | Admin Event Attendee List page | Admin list, filters, missing-event, unauthenticated, and attendee-denial tests | COMPLETE |
| FR-12 | Dashboard & Reports | Admin-only dashboard and event operational report using active-only capacity accounting | Admin Dashboard and Reports/CSV export | Dashboard totals, cancelled-capacity, event-report, filters, export, and authorization tests | COMPLETE |
| FR-13 | Check-in | Admin-only active check-in data plus safe event-specific attendee data access | Responsive Admin Event Attendee List / check-in view | Active/cancelled display, capacity summary, search/filter, and authorization tests | COMPLETE |
