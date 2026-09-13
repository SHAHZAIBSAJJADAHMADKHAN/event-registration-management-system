"""Authentication identity endpoints; no login or signup flow is implemented here."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.auth import require_authenticated_user
from app.schemas.auth import AuthenticatedUser, CurrentUserResponse

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/me", response_model=CurrentUserResponse)
async def get_current_user(
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> AuthenticatedUser:
    """Return the currently authenticated user's server-authoritative profile."""
    return user
