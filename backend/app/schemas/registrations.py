"""Attendee registration lifecycle response contracts."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.foundation import EventStatus, RegistrationStatus


class RegistrationEventSummary(BaseModel):
    id: UUID
    title: str
    starts_at: datetime
    location: str
    status: EventStatus


class RegistrationResponse(BaseModel):
    id: UUID
    event_id: UUID
    status: RegistrationStatus
    created_at: datetime
    updated_at: datetime
    event: RegistrationEventSummary


class CurrentRegistrationResponse(BaseModel):
    registration_id: UUID | None = None
    status: RegistrationStatus | None = None
