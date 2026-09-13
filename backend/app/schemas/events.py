"""Request and response contracts for admin event management."""

from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.foundation import EventStatus


class EventTextFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10000)
    starts_at: datetime
    location: str = Field(min_length=1, max_length=300)
    capacity: int = Field(gt=0)

    @field_validator("title", "description", "location")
    @classmethod
    def require_nonblank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value must not be blank.")
        return value

    @field_validator("starts_at")
    @classmethod
    def require_timezone_aware_schedule(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("starts_at must include a UTC offset or timezone.")
        return value


class EventCreate(EventTextFields):
    """New events may be created as a draft or a valid published event."""

    status: EventStatus = EventStatus.DRAFT

    @model_validator(mode="after")
    def validate_creation_status(self) -> "EventCreate":
        if self.status not in {EventStatus.DRAFT, EventStatus.PUBLISHED}:
            raise ValueError("New events may only be created with draft or published status.")
        if self.status is EventStatus.PUBLISHED and self.starts_at <= datetime.now(timezone.utc):
            raise ValueError("Published events must be scheduled in the future.")
        return self


class EventUpdate(BaseModel):
    """Mutable event details; status changes use the dedicated transition endpoint."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=10000)
    starts_at: datetime | None = None
    location: str | None = Field(default=None, min_length=1, max_length=300)
    capacity: int | None = Field(default=None, gt=0)

    @field_validator("title", "description", "location")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Value must not be blank.")
        return value

    @field_validator("starts_at")
    @classmethod
    def require_optional_timezone_aware_schedule(
        cls, value: datetime | None
    ) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("starts_at must include a UTC offset or timezone.")
        return value

    @model_validator(mode="after")
    def require_at_least_one_change(self) -> "EventUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one event field must be supplied.")
        return self


class EventStatusTransition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: EventStatus


class EventResponse(BaseModel):
    id: UUID
    title: str
    description: str
    starts_at: datetime
    location: str
    capacity: int
    status: EventStatus
    created_by: UUID
    created_at: datetime
    updated_at: datetime
