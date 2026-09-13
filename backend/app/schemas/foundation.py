"""Small validation models shared by future event and registration services."""

from enum import StrEnum

from pydantic import BaseModel, Field


class EventStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RegistrationStatus(StrEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"


class EventFoundationInput(BaseModel):
    """Validation contract mirroring foundational event database constraints."""

    capacity: int = Field(gt=0)
    status: EventStatus


class RegistrationFoundationInput(BaseModel):
    """Validation contract mirroring foundational registration status values."""

    status: RegistrationStatus
