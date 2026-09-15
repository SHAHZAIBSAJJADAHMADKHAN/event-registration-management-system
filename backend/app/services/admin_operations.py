"""Business rules for administrator attendee lists, reporting, and totals."""

from uuid import UUID

from app.core.errors import APIError
from app.database.admin_operations import AdminOperationsRepository
from app.schemas.admin_operations import (
    AdminEventReportRow,
    AdminAttendeeRegistration,
    AdminDashboardSummary,
    AdminEventDetailedReport,
    EventOperationalSummary,
)
from app.schemas.foundation import RegistrationStatus


class AdminOperationsService:
    def __init__(self, repository: AdminOperationsRepository) -> None:
        self._repository = repository

    def _event_or_404(self, event_id: UUID) -> dict[str, object]:
        event = self._repository.get_event(event_id)
        if event is None:
            raise APIError(404, "event_not_found", "The event does not exist.")
        return event

    def _attendee_rows(
        self, event_id: UUID, registration_status: RegistrationStatus | None = None,
        search: str | None = None,
    ) -> list[AdminAttendeeRegistration]:
        event = self._event_or_404(event_id)
        registrations = self._repository.list_event_registrations(event_id, registration_status)
        attendee_ids = list({UUID(str(row["attendee_id"])) for row in registrations})
        profiles = self._repository.profiles(attendee_ids)
        emails = {attendee_id: self._repository.attendee_email(attendee_id) for attendee_id in attendee_ids}
        normalized_search = search.strip().casefold() if search else None
        rows: list[AdminAttendeeRegistration] = []
        for registration in registrations:
            attendee_id = UUID(str(registration["attendee_id"]))
            profile = profiles.get(attendee_id, {})
            name = profile.get("full_name")
            email = emails[attendee_id]
            if normalized_search and normalized_search not in " ".join(
                value.casefold() for value in (str(name or ""), str(email or ""))
            ):
                continue
            rows.append(
                AdminAttendeeRegistration(
                    registration_id=registration["id"],
                    registration_status=registration["status"],
                    registered_at=registration["created_at"],
                    attendee_id=attendee_id,
                    attendee_name=name if isinstance(name, str) else None,
                    attendee_email=email,
                    event_id=event_id,
                    event_title=str(event["title"]),
                )
            )
        return rows

    def attendee_list(
        self, event_id: UUID, registration_status: RegistrationStatus | None = None,
        search: str | None = None,
    ) -> list[AdminAttendeeRegistration]:
        return self._attendee_rows(event_id, registration_status, search)

    def operational_summary(self, event_id: UUID) -> EventOperationalSummary:
        event = self._event_or_404(event_id)
        registrations = self._repository.list_event_registrations(event_id)
        active = sum(row["status"] == RegistrationStatus.APPROVED.value for row in registrations)
        cancelled = sum(row["status"] == RegistrationStatus.CANCELLED.value for row in registrations)
        capacity = int(event["capacity"])
        return EventOperationalSummary(
            event_id=event_id,
            event_title=str(event["title"]),
            capacity=capacity,
            active_registrations=active,
            cancelled_registrations=cancelled,
            remaining_availability=max(capacity - active, 0),
        )

    def detailed_event_report(self, event_id: UUID) -> AdminEventDetailedReport:
        event = self._event_or_404(event_id)
        registrations = self._repository.list_event_registrations(event_id)
        counts = {status: 0 for status in RegistrationStatus}
        for registration in registrations:
            counts[RegistrationStatus(str(registration["status"]))] += 1
        capacity = int(event["capacity"])
        return AdminEventDetailedReport(
            event_id=event_id,
            event_title=str(event["title"]),
            starts_at=event["starts_at"],
            location=str(event["location"]),
            status=event["status"],
            capacity=capacity,
            remaining_availability=max(capacity - counts[RegistrationStatus.APPROVED], 0),
            registration_counts=counts,
            registrations=self._attendee_rows(event_id),
        )

    def dashboard(self) -> AdminDashboardSummary:
        events = self._repository.list_events()
        registrations = self._repository.list_registrations()
        active_by_event: dict[str, int] = {}
        active_registrations = 0
        for registration in registrations:
            if registration["status"] == RegistrationStatus.APPROVED.value:
                active_registrations += 1
                event_id = str(registration["event_id"])
                active_by_event[event_id] = active_by_event.get(event_id, 0) + 1
        available_capacity = sum(
            max(int(event["capacity"]) - active_by_event.get(str(event["id"]), 0), 0)
            for event in events
        )
        return AdminDashboardSummary(
            total_events=len(events),
            total_registrations=len(registrations),
            active_registrations=active_registrations,
            available_capacity=available_capacity,
        )

    def event_report(self) -> list[AdminEventReportRow]:
        registrations = self._repository.list_registrations()
        counts: dict[str, dict[str, int]] = {}
        for registration in registrations:
            event_counts = counts.setdefault(str(registration["event_id"]), {"approved": 0, "cancelled": 0})
            if registration["status"] in event_counts:
                event_counts[registration["status"]] += 1
        rows = []
        for event in self._repository.list_events():
            event_counts = counts.get(str(event["id"]), {"approved": 0, "cancelled": 0})
            capacity = int(event["capacity"])
            rows.append(AdminEventReportRow(
                event_id=event["id"], event_title=str(event["title"]), starts_at=event["starts_at"],
                location=str(event["location"]), status=str(event["status"]), capacity=capacity,
                active_registrations=event_counts["approved"], cancelled_registrations=event_counts["cancelled"],
                remaining_availability=max(capacity - event_counts["approved"], 0),
            ))
        return rows

    def check_in_report(self, event_id: UUID) -> list[AdminAttendeeRegistration]:
        return self._attendee_rows(event_id, RegistrationStatus.APPROVED)
