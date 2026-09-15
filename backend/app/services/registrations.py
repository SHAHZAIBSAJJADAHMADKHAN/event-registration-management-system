"""Business rules for attendee registration, cancellation, and history."""

from datetime import datetime, timezone
from uuid import UUID

from app.core.errors import APIError
from app.database.registrations import RegistrationDatabaseError, RegistrationRepository
from app.schemas.auth import AuthenticatedUser
from app.schemas.registrations import RegistrationResponse
from app.schemas.registrations import CurrentRegistrationResponse
from app.services.lifecycle import EventLifecycleService
from app.services.notifications import NotificationService


class RegistrationService:
    def __init__(
        self,
        repository: RegistrationRepository,
        notifications: NotificationService | None = None,
        lifecycle: EventLifecycleService | None = None,
    ) -> None:
        self._repository = repository
        self._notifications = notifications
        self._lifecycle = lifecycle

    def _reconcile_overdue_events(self) -> None:
        if self._lifecycle is not None:
            self._lifecycle.reconcile_overdue_events()

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

    @staticmethod
    def _cancellation_is_closed(event: dict[str, object]) -> bool:
        if event["status"] in {"completed", "cancelled"}:
            return True
        ends_at = event.get("ends_at")
        if ends_at is None:
            return False
        parsed_ends_at = (
            ends_at
            if isinstance(ends_at, datetime)
            else datetime.fromisoformat(str(ends_at).replace("Z", "+00:00"))
        )
        return parsed_ends_at <= datetime.now(timezone.utc)

    @staticmethod
    def _cancellation_closed_error() -> APIError:
        return APIError(
            409,
            "event_cancellation_closed",
            "Registration cancellation is not available because this event has ended or been closed.",
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
        self._reconcile_overdue_events()
        registrations = self._repository.list_owned(attendee.id)
        events = self._repository.get_events(
            [UUID(str(registration["event_id"])) for registration in registrations]
        )
        return [self._response(registration, events) for registration in registrations]

    def get_mine(
        self, registration_id: UUID, attendee: AuthenticatedUser
    ) -> RegistrationResponse:
        self._reconcile_overdue_events()
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
        self._reconcile_overdue_events()
        existing = self._repository.get_owned(registration_id, attendee.id)
        if existing is None:
            raise APIError(404, "registration_not_found", "The registration does not exist.")
        if existing["status"] not in {"pending", "approved"}:
            raise APIError(
                409,
                "registration_not_cancellable",
                "This registration cannot be cancelled.",
            )

        event_id = UUID(str(existing["event_id"]))
        event = self._repository.get_events([event_id]).get(event_id)
        if event is None:
            raise APIError(404, "event_not_found", "The related event does not exist.")
        if self._cancellation_is_closed(event):
            raise self._cancellation_closed_error()

        try:
            cancelled = self._repository.cancel_owned_open(registration_id, attendee.id)
        except RegistrationDatabaseError as error:
            if "event not found" in error.message.lower():
                raise APIError(404, "event_not_found", "The related event does not exist.") from error
            if "cancellation is closed" in error.message.lower():
                raise self._cancellation_closed_error() from error
            raise APIError(
                409,
                "registration_not_cancellable",
                "This registration cannot be cancelled.",
            ) from error
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
