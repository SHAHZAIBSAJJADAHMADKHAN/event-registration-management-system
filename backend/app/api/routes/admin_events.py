"""Admin-only event management endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.config import Settings, get_settings
from app.database.events import EventRepository
from app.dependencies.auth import require_admin
from app.schemas.auth import AuthenticatedUser
from app.schemas.events import EventCreate, EventResponse, EventStatusTransition, EventUpdate
from app.services.events import EventService

router = APIRouter(prefix="/admin/events", tags=["admin events"])


def get_event_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> EventService:
    return EventService(EventRepository(settings))


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: EventCreate,
    admin: Annotated[AuthenticatedUser, Depends(require_admin)],
    service: Annotated[EventService, Depends(get_event_service)],
) -> EventResponse:
    return service.create(payload, admin)


@router.get("", response_model=list[EventResponse])
async def list_events(
    _: Annotated[AuthenticatedUser, Depends(require_admin)],
    service: Annotated[EventService, Depends(get_event_service)],
) -> list[EventResponse]:
    return service.list_all()


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: UUID,
    _: Annotated[AuthenticatedUser, Depends(require_admin)],
    service: Annotated[EventService, Depends(get_event_service)],
) -> EventResponse:
    return service.get(event_id)


@router.patch("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: UUID,
    payload: EventUpdate,
    _: Annotated[AuthenticatedUser, Depends(require_admin)],
    service: Annotated[EventService, Depends(get_event_service)],
) -> EventResponse:
    return service.update(event_id, payload)


@router.patch("/{event_id}/status", response_model=EventResponse)
async def transition_event_status(
    event_id: UUID,
    payload: EventStatusTransition,
    _: Annotated[AuthenticatedUser, Depends(require_admin)],
    service: Annotated[EventService, Depends(get_event_service)],
) -> EventResponse:
    return service.transition(event_id, payload)
