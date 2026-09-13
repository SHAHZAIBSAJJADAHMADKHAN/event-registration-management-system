"""Business rules for attendee registration, cancellation, and history."""

from uuid import UUID

from app.core.errors import APIError
from app.database.registrations import RegistrationDatabaseError, RegistrationRepository
from app.schemas.auth import AuthenticatedUser
from app.schemas.registrations import RegistrationResponse


class RegistrationService:
    def __init__(self, repository: RegistrationRepository) -> None:
        self._repository = repository

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
                "You already have an active registration for this event.",
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
            registration = self._repository.create_atomic(event_id, attendee.id)
        except RegistrationDatabaseError as error:
            raise self._atomic_failure(error)

        return self._response(registration, self._repository.get_events([event_id]))

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
        if existing["status"] == "cancelled":
            raise APIError(
                409,
                "registration_already_cancelled",
                "This registration is already cancelled.",
            )

        cancelled = self._repository.cancel_owned_active(registration_id, attendee.id)
        if cancelled is None:
            raise APIError(
                409,
                "registration_already_cancelled",
                "This registration is already cancelled.",
            )
        return self._response(
            cancelled,
            self._repository.get_events([UUID(str(cancelled["event_id"]))]),
        )
