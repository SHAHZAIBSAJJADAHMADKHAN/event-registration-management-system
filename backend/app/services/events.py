"""Business rules for admin event management."""

from uuid import UUID

from app.core.errors import APIError
from app.database.events import EventRepository
from app.schemas.auth import AuthenticatedUser
from app.schemas.events import EventCreate, EventResponse, EventStatusTransition, EventUpdate
from app.schemas.foundation import EventStatus
from app.services.lifecycle import EventLifecycleService
from postgrest.exceptions import APIError as PostgrestAPIError


_ALLOWED_TRANSITIONS: dict[EventStatus, set[EventStatus]] = {
    EventStatus.DRAFT: {EventStatus.PUBLISHED, EventStatus.CANCELLED},
    EventStatus.PUBLISHED: {EventStatus.COMPLETED, EventStatus.CANCELLED},
    EventStatus.COMPLETED: set(),
    EventStatus.CANCELLED: set(),
}


class EventService:
    def __init__(
        self, repository: EventRepository, lifecycle: EventLifecycleService | None = None
    ) -> None:
        self._repository = repository
        self._lifecycle = lifecycle

    def _reconcile_overdue_events(self) -> None:
        if self._lifecycle is not None:
            self._lifecycle.reconcile_overdue_events()

    @staticmethod
    def _response(event: dict[str, object]) -> EventResponse:
        return EventResponse.model_validate(event)

    def create(self, payload: EventCreate, admin: AuthenticatedUser) -> EventResponse:
        values = payload.model_dump(mode="json")
        values["created_by"] = str(admin.id)
        return self._response(self._repository.create(values))

    def list_all(self) -> list[EventResponse]:
        self._reconcile_overdue_events()
        return [self._response(event) for event in self._repository.list_all()]

    def get(self, event_id: UUID) -> EventResponse:
        self._reconcile_overdue_events()
        event = self._repository.get(event_id)
        if event is None:
            raise APIError(404, "event_not_found", "The event does not exist.")
        return self._response(event)

    def update(self, event_id: UUID, payload: EventUpdate) -> EventResponse:
        event = self.get(event_id)
        values = payload.model_dump(mode="json", exclude_unset=True)

        if "starts_at" in values or "ends_at" in values:
            starts_at = payload.starts_at or event.starts_at
            ends_at = payload.ends_at if "ends_at" in values else event.ends_at
            if ends_at is not None and ends_at <= starts_at:
                raise APIError(422, "invalid_event_schedule", "Event end time must be later than its start time.")

        if "capacity" in values:
            approved_count = self._repository.count_approved_registrations(event_id)
            if values["capacity"] < approved_count:
                raise APIError(
                    409,
                    "capacity_below_approved_registrations",
                    "Capacity cannot be lower than approved registrations.",
                )

        updated = self._repository.update(event_id, values)
        if updated is None:
            raise APIError(404, "event_not_found", "The event does not exist.")
        return self._response(updated)

    def transition(
        self, event_id: UUID, payload: EventStatusTransition
    ) -> EventResponse:
        event = self.get(event_id)
        target = payload.status
        if target not in _ALLOWED_TRANSITIONS[event.status]:
            raise APIError(
                409,
                "invalid_event_transition",
                f"Cannot transition an event from {event.status} to {target}.",
            )

        updated = self._repository.update(event_id, {"status": target.value})
        if updated is None:
            raise APIError(404, "event_not_found", "The event does not exist.")
        return self._response(updated)

    def delete(self, event_id: UUID) -> None:
        # Provides a stable 404 contract while the RPC repeats the existence
        # check inside its transaction to protect against races.
        self.get(event_id)
        try:
            deleted = self._repository.delete_hard_atomic(event_id)
        except PostgrestAPIError as error:
            if "not found" in error.message.lower():
                raise APIError(404, "event_not_found", "This event could not be found.") from error
            raise APIError(503, "event_delete_failed", "This event could not be deleted.") from error
        except Exception as error:
            raise APIError(503, "event_delete_failed", "This event could not be deleted.") from error
        if not deleted:
            raise APIError(503, "event_delete_failed", "This event could not be deleted.")
