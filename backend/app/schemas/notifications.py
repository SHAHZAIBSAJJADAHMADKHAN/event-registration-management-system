from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class NotificationResponse(BaseModel):
    id: UUID
    type: str
    title: str
    message: str
    is_read: bool
    event_id: UUID | None = None
    registration_id: UUID | None = None
    created_at: datetime


class UnreadNotificationCount(BaseModel):
    unread_count: int = Field(ge=0)
