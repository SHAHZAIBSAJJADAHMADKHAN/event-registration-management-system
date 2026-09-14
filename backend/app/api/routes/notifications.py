from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, status
from app.core.config import Settings, get_settings
from app.database.notifications import NotificationRepository
from app.dependencies.auth import require_authenticated_user
from app.schemas.auth import AuthenticatedUser
from app.schemas.notifications import NotificationResponse, UnreadNotificationCount
from app.services.notifications import NotificationService

router = APIRouter(tags=["notifications"])
def get_notification_service(settings: Annotated[Settings, Depends(get_settings)]) -> NotificationService:
    return NotificationService(NotificationRepository(settings))

@router.get("/me/notifications", response_model=list[NotificationResponse])
async def list_notifications(user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)], service: Annotated[NotificationService, Depends(get_notification_service)]):
    return service.list_mine(user.id)

@router.get("/me/notifications/unread-count", response_model=UnreadNotificationCount)
async def unread_count(user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)], service: Annotated[NotificationService, Depends(get_notification_service)]):
    return service.unread_count(user.id)

@router.patch("/me/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_read(user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)], service: Annotated[NotificationService, Depends(get_notification_service)]):
    service.mark_all_read(user.id)

@router.patch("/me/notifications/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(notification_id: UUID, user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)], service: Annotated[NotificationService, Depends(get_notification_service)]):
    return service.mark_read(notification_id, user.id)
