"""Attendee-only upcoming event discovery endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.database.events import EventRepository
from app.database.lifecycle import EventLifecycleRepository
from app.dependencies.auth import require_attendee
from app.schemas.auth import AuthenticatedUser
from app.schemas.discovery import DiscoverableEventResponse
from app.services.discovery import EventDiscoveryService
from app.services.lifecycle import EventLifecycleService

router = APIRouter(prefix="/events", tags=["event discovery"])


def get_event_discovery_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> EventDiscoveryService:
    return EventDiscoveryService(
        EventRepository(settings), EventLifecycleService(EventLifecycleRepository(settings))
    )


@router.get("", response_model=list[DiscoverableEventResponse])
async def list_upcoming_events(
    _: Annotated[AuthenticatedUser, Depends(require_attendee)],
    service: Annotated[EventDiscoveryService, Depends(get_event_discovery_service)],
) -> list[DiscoverableEventResponse]:
    return service.list_upcoming()


@router.get("/{event_id}", response_model=DiscoverableEventResponse)
async def get_upcoming_event(
    event_id: UUID,
    _: Annotated[AuthenticatedUser, Depends(require_attendee)],
    service: Annotated[EventDiscoveryService, Depends(get_event_discovery_service)],
) -> DiscoverableEventResponse:
    return service.get_upcoming(event_id)
