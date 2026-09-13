"""Trusted database access for admin-only attendee operations."""

from uuid import UUID

from app.core.config import Settings
from app.database.client import create_secret_client
from app.schemas.foundation import RegistrationStatus


class AdminOperationsRepository:
    """Reads operational data through the backend-only Supabase client."""

    def __init__(self, settings: Settings) -> None:
        self._client = create_secret_client(settings)

    def get_event(self, event_id: UUID) -> dict[str, object] | None:
        response = (
            self._client.table("events")
            .select("id,title,starts_at,location,status,capacity")
            .eq("id", str(event_id))
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def list_event_registrations(
        self, event_id: UUID, registration_status: RegistrationStatus | None = None
    ) -> list[dict[str, object]]:
        query = (
            self._client.table("registrations")
            .select("id,event_id,attendee_id,status,created_at")
            .eq("event_id", str(event_id))
            .order("created_at")
        )
        if registration_status is not None:
            query = query.eq("status", registration_status.value)
        return query.execute().data

    def profiles(self, attendee_ids: list[UUID]) -> dict[UUID, dict[str, object]]:
        if not attendee_ids:
            return {}
        response = (
            self._client.table("profiles")
            .select("id,full_name")
            .in_("id", [str(attendee_id) for attendee_id in attendee_ids])
            .execute()
        )
        return {UUID(profile["id"]): profile for profile in response.data}

    def attendee_email(self, attendee_id: UUID) -> str | None:
        """Return only the email needed for an authorised operations view."""
        response = self._client.auth.admin.get_user_by_id(str(attendee_id))
        user = getattr(response, "user", None)
        return getattr(user, "email", None) if user is not None else None

    def list_events(self) -> list[dict[str, object]]:
        return self._client.table("events").select("id,title,starts_at,location,status,capacity").order("starts_at").execute().data

    def list_registrations(self) -> list[dict[str, object]]:
        return self._client.table("registrations").select("id,event_id,status").execute().data
