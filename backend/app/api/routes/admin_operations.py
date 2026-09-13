"""Admin-only attendee management, reporting, and CSV export endpoints."""

import csv
from io import StringIO
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.core.config import Settings, get_settings
from app.database.admin_operations import AdminOperationsRepository
from app.dependencies.auth import require_admin
from app.schemas.admin_operations import (
    AdminAttendeeRegistration,
    AdminDashboardSummary,
    AdminEventReportRow,
    EventOperationalSummary,
)
from app.schemas.auth import AuthenticatedUser
from app.schemas.foundation import RegistrationStatus
from app.services.admin_operations import AdminOperationsService

router = APIRouter(prefix="/admin", tags=["admin operations"])


def get_admin_operations_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AdminOperationsService:
    return AdminOperationsService(AdminOperationsRepository(settings))


def _csv_cell(value: object) -> object:
    text = str(value)
    return f"'{text}" if text.startswith(("=", "+", "-", "@")) else text


def _attendee_csv(rows: list[AdminAttendeeRegistration]) -> str:
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow([
        "Registration ID", "Registration Status", "Registered At", "Attendee ID",
        "Attendee Name", "Attendee Email", "Event ID", "Event Title",
    ])
    for row in rows:
        writer.writerow([_csv_cell(value) for value in (
            row.registration_id, row.registration_status, row.registered_at.isoformat(),
            row.attendee_id, row.attendee_name or "", row.attendee_email or "",
            row.event_id, row.event_title,
        )])
    return output.getvalue()


@router.get("/dashboard", response_model=AdminDashboardSummary)
async def dashboard(
    _: Annotated[AuthenticatedUser, Depends(require_admin)],
    service: Annotated[AdminOperationsService, Depends(get_admin_operations_service)],
) -> AdminDashboardSummary:
    return service.dashboard()


@router.get("/reports/events", response_model=list[AdminEventReportRow])
async def event_report(
    _: Annotated[AuthenticatedUser, Depends(require_admin)],
    service: Annotated[AdminOperationsService, Depends(get_admin_operations_service)],
) -> list[AdminEventReportRow]:
    return service.event_report()


@router.get("/events/{event_id}/attendees", response_model=list[AdminAttendeeRegistration])
async def attendee_list(
    event_id: UUID,
    _: Annotated[AuthenticatedUser, Depends(require_admin)],
    service: Annotated[AdminOperationsService, Depends(get_admin_operations_service)],
    registration_status: RegistrationStatus | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, min_length=1, max_length=120),
) -> list[AdminAttendeeRegistration]:
    return service.attendee_list(event_id, registration_status, search)


@router.get("/events/{event_id}/summary", response_model=EventOperationalSummary)
async def event_summary(
    event_id: UUID,
    _: Annotated[AuthenticatedUser, Depends(require_admin)],
    service: Annotated[AdminOperationsService, Depends(get_admin_operations_service)],
) -> EventOperationalSummary:
    return service.operational_summary(event_id)


@router.get("/events/{event_id}/check-in", response_model=list[AdminAttendeeRegistration])
async def check_in_report(
    event_id: UUID,
    _: Annotated[AuthenticatedUser, Depends(require_admin)],
    service: Annotated[AdminOperationsService, Depends(get_admin_operations_service)],
) -> list[AdminAttendeeRegistration]:
    return service.check_in_report(event_id)


@router.get("/events/{event_id}/attendees/export.csv")
async def export_attendees_csv(
    event_id: UUID,
    _: Annotated[AuthenticatedUser, Depends(require_admin)],
    service: Annotated[AdminOperationsService, Depends(get_admin_operations_service)],
    registration_status: RegistrationStatus | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, min_length=1, max_length=120),
) -> Response:
    content = _attendee_csv(service.attendee_list(event_id, registration_status, search))
    return Response(
        content=content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="event-{event_id}-attendees.csv"',
            "X-Content-Type-Options": "nosniff",
        },
    )
