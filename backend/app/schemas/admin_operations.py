"""Response contracts for admin attendee operations and reporting."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.foundation import EventStatus, RegistrationStatus


class AdminAttendeeRegistration(BaseModel):
    registration_id: UUID
    registration_status: RegistrationStatus
    registered_at: datetime
    attendee_id: UUID
    attendee_name: str | None
    attendee_email: str | None
    event_id: UUID
    event_title: str


class EventOperationalSummary(BaseModel):
    event_id: UUID
    event_title: str
    capacity: int = Field(gt=0)
    active_registrations: int = Field(ge=0)
    cancelled_registrations: int = Field(ge=0)
    remaining_availability: int = Field(ge=0)


class AdminEventReportRow(EventOperationalSummary):
    starts_at: datetime
    location: str
    status: EventStatus


class AdminEventDetailedReport(BaseModel):
    event_id: UUID
    event_title: str
    starts_at: datetime
    location: str
    status: EventStatus
    capacity: int = Field(gt=0)
    remaining_availability: int = Field(ge=0)
    registration_counts: dict[RegistrationStatus, int]
    registrations: list[AdminAttendeeRegistration]


class AdminDashboardSummary(BaseModel):
    total_events: int = Field(ge=0)
    total_registrations: int = Field(ge=0)
    active_registrations: int = Field(ge=0)
    available_capacity: int = Field(ge=0)
