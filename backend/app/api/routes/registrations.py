"""Attendee-owned registration lifecycle endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.config import Settings, get_settings
from app.database.registrations import RegistrationRepository
from app.database.notifications import NotificationRepository
from app.dependencies.auth import require_attendee
from app.schemas.auth import AuthenticatedUser
from app.schemas.registrations import CurrentRegistrationResponse, RegistrationResponse
from app.services.registrations import RegistrationService
from app.services.notifications import NotificationService

router = APIRouter(tags=["registrations"])


def get_registration_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> RegistrationService:
    return RegistrationService(RegistrationRepository(settings), NotificationService(NotificationRepository(settings)))


@router.post(
    "/events/{event_id}/registrations",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_registration(
    event_id: UUID,
    attendee: Annotated[AuthenticatedUser, Depends(require_attendee)],
    service: Annotated[RegistrationService, Depends(get_registration_service)],
) -> RegistrationResponse:
    return service.create(event_id, attendee)


@router.get("/events/{event_id}/my-registration", response_model=CurrentRegistrationResponse)
async def current_registration(event_id: UUID, attendee: Annotated[AuthenticatedUser, Depends(require_attendee)], service: Annotated[RegistrationService, Depends(get_registration_service)]) -> CurrentRegistrationResponse:
    return service.current_for_event(event_id, attendee)


@router.get("/me/registrations", response_model=list[RegistrationResponse])
async def list_my_registrations(
    attendee: Annotated[AuthenticatedUser, Depends(require_attendee)],
    service: Annotated[RegistrationService, Depends(get_registration_service)],
) -> list[RegistrationResponse]:
    return service.list_mine(attendee)


@router.get("/me/registrations/{registration_id}", response_model=RegistrationResponse)
async def get_my_registration(
    registration_id: UUID,
    attendee: Annotated[AuthenticatedUser, Depends(require_attendee)],
    service: Annotated[RegistrationService, Depends(get_registration_service)],
) -> RegistrationResponse:
    return service.get_mine(registration_id, attendee)


@router.patch(
    "/me/registrations/{registration_id}/cancel",
    response_model=RegistrationResponse,
)
async def cancel_registration(
    registration_id: UUID,
    attendee: Annotated[AuthenticatedUser, Depends(require_attendee)],
    service: Annotated[RegistrationService, Depends(get_registration_service)],
) -> RegistrationResponse:
    return service.cancel(registration_id, attendee)
