"""Business rules for attendee registration, cancellation, and history."""

from uuid import UUID

from app.core.errors import APIError
from app.database.registrations import RegistrationDatabaseError, RegistrationRepository
from app.schemas.auth import AuthenticatedUser
from app.schemas.registrations import RegistrationResponse
from app.schemas.registrations import CurrentRegistrationResponse
from app.services.notifications import NotificationService


class RegistrationService:
    def __init__(self, repository: RegistrationRepository, notifications: NotificationService | None = None) -> None:
        self._repository = repository
        self._notifications = notifications

    @staticmethod
    def _response(
        registration: dict[str, object], events: dict[UUID, dict[str, object]]
    ) -> RegistrationResponse:
        event_id = UUID(str(registration["event_id"]))
        event = events.get(event_id)
        if event is None:
            raise APIError(404, "event_not_found", "The related event does not exist.")
        return RegistrationResponse(
            id=registration["id"],
            event_id=event_id,
            status=registration["status"],
            created_at=registration["created_at"],
            updated_at=registration["updated_at"],
            event=event,
        )

    @staticmethod
    def _atomic_failure(error: RegistrationDatabaseError) -> APIError:
        message = error.message.lower()
        if "event not found" in message:
            return APIError(404, "event_not_found", "The event does not exist.")
        if "already exists" in message:
            return APIError(
                409,
                "duplicate_registration",
                "You already have an open registration request for this event.",
            )
        if "capacity" in message:
            return APIError(409, "event_full", "This event is full.")
        if "closed" in message or "past" in message:
            return APIError(
                409,
                "event_not_eligible",
                "Registration is not available for this event.",
            )
        return APIError(
            503,
            "registration_unavailable",
            "Registration is temporarily unavailable.",
        )

    def create(self, event_id: UUID, attendee: AuthenticatedUser) -> RegistrationResponse:
        try:
            registration = self._repository.create_request_atomic(event_id, attendee.id)
        except RegistrationDatabaseError as error:
            raise self._atomic_failure(error)

        response = self._response(registration, self._repository.get_events([event_id]))
        if self._notifications:
            self._notifications.create(attendee.id, "registration_request_submitted", "Registration request submitted", f"Your request for {response.event.title} was sent to the admin for approval.", event_id, UUID(str(registration["id"])))
            for admin_id in self._repository.admin_ids():
                self._notifications.create(admin_id, "new_registration_request", "New registration request", f"{attendee.full_name} requested to join {response.event.title}.", event_id, UUID(str(registration["id"])))
        return response

    def current_for_event(self, event_id: UUID, attendee: AuthenticatedUser) -> CurrentRegistrationResponse:
        row = self._repository.get_open_owned_for_event(event_id, attendee.id)
        return CurrentRegistrationResponse(registration_id=row["id"] if row else None, status=row["status"] if row else None)

    def list_mine(self, attendee: AuthenticatedUser) -> list[RegistrationResponse]:
        registrations = self._repository.list_owned(attendee.id)
        events = self._repository.get_events(
            [UUID(str(registration["event_id"])) for registration in registrations]
        )
        return [self._response(registration, events) for registration in registrations]

    def get_mine(
        self, registration_id: UUID, attendee: AuthenticatedUser
    ) -> RegistrationResponse:
        registration = self._repository.get_owned(registration_id, attendee.id)
        if registration is None:
            raise APIError(404, "registration_not_found", "The registration does not exist.")
        return self._response(
            registration,
            self._repository.get_events([UUID(str(registration["event_id"]))]),
        )

    def cancel(
        self, registration_id: UUID, attendee: AuthenticatedUser
    ) -> RegistrationResponse:
        existing = self._repository.get_owned(registration_id, attendee.id)
        if existing is None:
            raise APIError(404, "registration_not_found", "The registration does not exist.")
        if existing["status"] not in {"pending", "approved"}:
            raise APIError(
                409,
                "registration_not_cancellable",
                "This registration cannot be cancelled.",
            )

        cancelled = self._repository.cancel_owned_open(registration_id, attendee.id)
        if cancelled is None:
            raise APIError(
                409,
                "registration_not_cancellable",
                "This registration cannot be cancelled.",
            )
        return self._response(
            cancelled,
            self._repository.get_events([UUID(str(cancelled["event_id"]))]),
        )
