from uuid import UUID
from app.core.errors import APIError
from app.database.notifications import NotificationRepository
from app.schemas.notifications import NotificationResponse, UnreadNotificationCount


class NotificationService:
    def __init__(self, repository: NotificationRepository) -> None:
        self._repository = repository

    def create(self, user_id: UUID, type: str, title: str, message: str, event_id: UUID | None, registration_id: UUID | None) -> None:
        self._repository.create({"user_id": str(user_id), "type": type, "title": title, "message": message, "event_id": str(event_id) if event_id else None, "registration_id": str(registration_id) if registration_id else None})

    def list_mine(self, user_id: UUID) -> list[NotificationResponse]:
        return [NotificationResponse.model_validate(row) for row in self._repository.list_owned(user_id)]

    def unread_count(self, user_id: UUID) -> UnreadNotificationCount:
        return UnreadNotificationCount(unread_count=self._repository.unread_count(user_id))

    def mark_read(self, notification_id: UUID, user_id: UUID) -> NotificationResponse:
        row = self._repository.mark_read(notification_id, user_id)
        if row is None:
            raise APIError(404, "notification_not_found", "The notification does not exist.")
        return NotificationResponse.model_validate(row)

    def mark_all_read(self, user_id: UUID) -> None:
        self._repository.mark_all_read(user_id)
