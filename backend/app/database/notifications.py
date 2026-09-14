from uuid import UUID
from app.core.config import Settings
from app.database.client import create_secret_client


class NotificationRepository:
    def __init__(self, settings: Settings) -> None:
        self._client = create_secret_client(settings)

    def create(self, values: dict[str, object]) -> dict[str, object]:
        return self._client.table("notifications").insert(values).execute().data[0]

    def list_owned(self, user_id: UUID) -> list[dict[str, object]]:
        return self._client.table("notifications").select("*").eq("user_id", str(user_id)).order("created_at", desc=True).execute().data

    def unread_count(self, user_id: UUID) -> int:
        response = self._client.table("notifications").select("id", count="exact").eq("user_id", str(user_id)).eq("is_read", False).execute()
        return response.count or 0

    def mark_read(self, notification_id: UUID, user_id: UUID) -> dict[str, object] | None:
        response = self._client.table("notifications").update({"is_read": True}).eq("id", str(notification_id)).eq("user_id", str(user_id)).execute()
        return response.data[0] if response.data else None

    def mark_all_read(self, user_id: UUID) -> None:
        self._client.table("notifications").update({"is_read": True}).eq("user_id", str(user_id)).eq("is_read", False).execute()
