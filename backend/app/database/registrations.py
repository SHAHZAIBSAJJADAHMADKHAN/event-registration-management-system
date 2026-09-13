"""Database access for attendee-owned registration operations."""

from uuid import UUID

from postgrest.exceptions import APIError as PostgrestAPIError

from app.core.config import Settings
from app.database.client import create_secret_client


class RegistrationDatabaseError(Exception):
    def __init__(self, code: str | None, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class RegistrationRepository:
    def __init__(self, settings: Settings) -> None:
        self._client = create_secret_client(settings)

    def create_atomic(self, event_id: UUID, attendee_id: UUID) -> dict[str, object]:
        try:
            return self._client.rpc(
                "create_registration_atomic",
                {"p_event_id": str(event_id), "p_attendee_id": str(attendee_id)},
            ).execute().data
        except PostgrestAPIError as error:
            raise RegistrationDatabaseError(error.code, error.message) from error

    def get_owned(self, registration_id: UUID, attendee_id: UUID) -> dict[str, object] | None:
        response = (
            self._client.table("registrations")
            .select("id,event_id,status,created_at,updated_at")
            .eq("id", str(registration_id))
            .eq("attendee_id", str(attendee_id))
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def list_owned(self, attendee_id: UUID) -> list[dict[str, object]]:
        return (
            self._client.table("registrations")
            .select("id,event_id,status,created_at,updated_at")
            .eq("attendee_id", str(attendee_id))
            .order("created_at", desc=True)
            .execute()
            .data
        )

    def cancel_owned_active(
        self, registration_id: UUID, attendee_id: UUID
    ) -> dict[str, object] | None:
        response = (
            self._client.table("registrations")
            .update({"status": "cancelled"})
            .eq("id", str(registration_id))
            .eq("attendee_id", str(attendee_id))
            .eq("status", "active")
            .execute()
        )
        return response.data[0] if response.data else None

    def get_events(self, event_ids: list[UUID]) -> dict[UUID, dict[str, object]]:
        if not event_ids:
            return {}
        response = (
            self._client.table("events")
            .select("id,title,starts_at,location,status")
            .in_("id", [str(event_id) for event_id in event_ids])
            .execute()
        )
        return {UUID(event["id"]): event for event in response.data}
