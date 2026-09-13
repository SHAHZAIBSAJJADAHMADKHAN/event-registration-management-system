"""Business rules for admin event management."""

from uuid import UUID

from app.core.errors import APIError
from app.database.events import EventRepository
from app.schemas.auth import AuthenticatedUser
from app.schemas.events import EventCreate, EventResponse, EventStatusTransition, EventUpdate
from app.schemas.foundation import EventStatus


_ALLOWED_TRANSITIONS: dict[EventStatus, set[EventStatus]] = {
    EventStatus.DRAFT: {EventStatus.PUBLISHED, EventStatus.CANCELLED},
    EventStatus.PUBLISHED: {EventStatus.COMPLETED, EventStatus.CANCELLED},
    EventStatus.COMPLETED: set(),
    EventStatus.CANCELLED: set(),
}


class EventService:
    def __init__(self, repository: EventRepository) -> None:
        self._repository = repository

    @staticmethod
    def _response(event: dict[str, object]) -> EventResponse:
        return EventResponse.model_validate(event)

    def create(self, payload: EventCreate, admin: AuthenticatedUser) -> EventResponse:
        values = payload.model_dump(mode="json")
        values["created_by"] = str(admin.id)
        return self._response(self._repository.create(values))

    def list_all(self) -> list[EventResponse]:
        return [self._response(event) for event in self._repository.list_all()]

    def get(self, event_id: UUID) -> EventResponse:
        event = self._repository.get(event_id)
        if event is None:
            raise APIError(404, "event_not_found", "The event does not exist.")
        return self._response(event)

    def update(self, event_id: UUID, payload: EventUpdate) -> EventResponse:
        self.get(event_id)
        values = payload.model_dump(mode="json", exclude_unset=True)

        if "capacity" in values:
            active_count = self._repository.count_active_registrations(event_id)
            if values["capacity"] < active_count:
                raise APIError(
                    409,
                    "capacity_below_active_registrations",
                    "Capacity cannot be lower than active registrations.",
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
