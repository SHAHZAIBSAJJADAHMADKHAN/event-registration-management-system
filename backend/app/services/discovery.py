"""Business rules for attendee event discovery."""

from datetime import datetime, timezone
from uuid import UUID

from app.core.errors import APIError
from app.database.events import EventRepository
from app.schemas.discovery import DiscoverableEventResponse


class EventDiscoveryService:
    def __init__(self, repository: EventRepository) -> None:
        self._repository = repository

    @staticmethod
    def _response(event: dict[str, object], active_count: int) -> DiscoverableEventResponse:
        capacity = int(event["capacity"])
        return DiscoverableEventResponse(
            id=event["id"],
            title=event["title"],
            description=event["description"],
            starts_at=event["starts_at"],
            location=event["location"],
            capacity=capacity,
            active_registration_count=active_count,
            remaining_availability=max(capacity - active_count, 0),
            status=event["status"],
        )

    def list_upcoming(self) -> list[DiscoverableEventResponse]:
        now = datetime.now(timezone.utc)
        events = self._repository.list_published_upcoming(now)
        counts = self._repository.approved_registration_counts(
            [UUID(str(event["id"])) for event in events]
        )
        return [
            self._response(event, counts.get(UUID(str(event["id"])), 0))
            for event in events
        ]

    def get_upcoming(self, event_id: UUID) -> DiscoverableEventResponse:
        event = self._repository.get_published_upcoming(event_id, datetime.now(timezone.utc))
        if event is None:
            raise APIError(404, "event_not_found", "The event is not available.")
        count = self._repository.approved_registration_counts([event_id]).get(event_id, 0)
        return self._response(event, count)
