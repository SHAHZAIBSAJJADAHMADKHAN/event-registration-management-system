"""Database access for administrative event operations."""

from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

from app.core.config import Settings
from app.database.client import create_secret_client


class EventRepository:
    def __init__(self, settings: Settings) -> None:
        self._client = create_secret_client(settings)

    def create(self, values: Mapping[str, object]) -> dict[str, object]:
        return self._client.table("events").insert(dict(values)).execute().data[0]

    def list_all(self) -> list[dict[str, object]]:
        return self._client.table("events").select("*").order("starts_at").execute().data

    def get(self, event_id: UUID) -> dict[str, object] | None:
        response = (
            self._client.table("events")
            .select("*")
            .eq("id", str(event_id))
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def update(self, event_id: UUID, values: Mapping[str, object]) -> dict[str, object] | None:
        response = (
            self._client.table("events")
            .update(dict(values))
            .eq("id", str(event_id))
            .execute()
        )
        return response.data[0] if response.data else self.get(event_id)

    def count_active_registrations(self, event_id: UUID) -> int:
        response = (
            self._client.table("registrations")
            .select("id", count="exact")
            .eq("event_id", str(event_id))
            .eq("status", "active")
            .execute()
        )
        return response.count or 0

    def list_published_upcoming(self, now: datetime) -> list[dict[str, object]]:
        return (
            self._client.table("events")
            .select("*")
            .eq("status", "published")
            .gt("starts_at", now.isoformat())
            .order("starts_at")
            .execute()
            .data
        )

    def get_published_upcoming(
        self, event_id: UUID, now: datetime
    ) -> dict[str, object] | None:
        response = (
            self._client.table("events")
            .select("*")
            .eq("id", str(event_id))
            .eq("status", "published")
            .gt("starts_at", now.isoformat())
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def active_registration_counts(self, event_ids: list[UUID]) -> dict[UUID, int]:
        if not event_ids:
            return {}
        response = (
            self._client.table("registrations")
            .select("event_id")
            .in_("event_id", [str(event_id) for event_id in event_ids])
            .eq("status", "active")
            .execute()
        )
        counts: dict[UUID, int] = {}
        for registration in response.data:
            event_id = UUID(registration["event_id"])
            counts[event_id] = counts.get(event_id, 0) + 1
        return counts
