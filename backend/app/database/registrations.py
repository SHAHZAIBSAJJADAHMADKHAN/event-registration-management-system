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

    def create_request_atomic(self, event_id: UUID, attendee_id: UUID) -> dict[str, object]:
        try:
            return self._client.rpc(
                "create_registration_request_atomic",
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

    def get_open_owned_for_event(self, event_id: UUID, attendee_id: UUID) -> dict[str, object] | None:
        response = self._client.table("registrations").select("id,status").eq("event_id", str(event_id)).eq("attendee_id", str(attendee_id)).in_("status", ["pending", "approved"]).limit(1).execute()
        return response.data[0] if response.data else None

    def admin_ids(self) -> list[UUID]:
        response = self._client.table("profiles").select("id").eq("role", "admin").execute()
        return [UUID(row["id"]) for row in response.data]

    def profiles(self, attendee_ids: list[UUID]) -> dict[UUID, dict[str, object]]:
        if not attendee_ids: return {}
        response = self._client.table("profiles").select("id,full_name").in_("id", [str(value) for value in attendee_ids]).execute()
        return {UUID(row["id"]): row for row in response.data}

    def attendee_email(self, attendee_id: UUID) -> str | None:
        user = getattr(self._client.auth.admin.get_user_by_id(str(attendee_id)), "user", None)
        return getattr(user, "email", None) if user else None

    def list_all(self, registration_status: str | None = None, event_id: UUID | None = None) -> list[dict[str, object]]:
        query = self._client.table("registrations").select("id,event_id,attendee_id,status,created_at,updated_at").order("created_at", desc=True)
        if registration_status: query = query.eq("status", registration_status)
        if event_id: query = query.eq("event_id", str(event_id))
        return query.execute().data

    def approve_atomic(self, registration_id: UUID) -> dict[str, object]:
        try: return self._client.rpc("approve_registration_atomic", {"p_registration_id": str(registration_id)}).execute().data
        except PostgrestAPIError as error: raise RegistrationDatabaseError(error.code, error.message) from error

    def reject_atomic(self, registration_id: UUID) -> dict[str, object]:
        try: return self._client.rpc("reject_registration_atomic", {"p_registration_id": str(registration_id)}).execute().data
        except PostgrestAPIError as error: raise RegistrationDatabaseError(error.code, error.message) from error

    def cancel_owned_open(
        self, registration_id: UUID, attendee_id: UUID
    ) -> dict[str, object] | None:
        try:
            return self._client.rpc(
                "cancel_registration_atomic",
                {
                    "p_registration_id": str(registration_id),
                    "p_attendee_id": str(attendee_id),
                },
            ).execute().data
        except PostgrestAPIError as error:
            raise RegistrationDatabaseError(error.code, error.message) from error

    def get_events(self, event_ids: list[UUID]) -> dict[UUID, dict[str, object]]:
        if not event_ids:
            return {}
        response = (
            self._client.table("events")
            .select("id,title,starts_at,ends_at,location,status")
            .in_("id", [str(event_id) for event_id in event_ids])
            .execute()
        )
        return {UUID(event["id"]): event for event in response.data}
