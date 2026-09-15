"""Attendee-facing event discovery response contracts."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.foundation import EventStatus


class DiscoverableEventResponse(BaseModel):
    id: UUID
    title: str
    description: str
    starts_at: datetime
    ends_at: datetime | None = None
    location: str
    capacity: int
    active_registration_count: int
    remaining_availability: int
    status: EventStatus
