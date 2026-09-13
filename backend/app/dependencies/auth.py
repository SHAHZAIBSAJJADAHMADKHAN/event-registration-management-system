"""Reusable FastAPI authentication, role, and ownership dependencies."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings
from app.core.security import JWTVerificationError, JWTVerifier, get_jwt_verifier
from app.database.profiles import ProfileRepository
from app.schemas.auth import AuthenticatedUser, UserRole

bearer_scheme = HTTPBearer(auto_error=False)


def _authentication_error(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": code, "message": message},
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_profile_repository(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ProfileRepository:
    return ProfileRepository(settings)


async def require_authenticated_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    verifier: Annotated[JWTVerifier, Depends(get_jwt_verifier)],
    profiles: Annotated[ProfileRepository, Depends(get_profile_repository)],
) -> AuthenticatedUser:
    """Verify a Bearer token and resolve its server-authoritative profile."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _authentication_error(
            "authentication_required", "A Bearer token is required."
        )

    try:
        claims = verifier.verify(credentials.credentials)
        user_id = UUID(str(claims["sub"]))
    except (JWTVerificationError, KeyError, ValueError):
        raise _authentication_error("invalid_token", "The access token is invalid.")

    try:
        user = profiles.get_authenticated_user(user_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "profile_lookup_unavailable",
                "message": "Authentication service is temporarily unavailable.",
            },
        )

    if user is None:
        raise _authentication_error(
            "profile_not_found", "No application profile exists for this identity."
        )
    return user


async def require_admin(
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> AuthenticatedUser:
    if user.role is not UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "admin_required", "message": "Administrator access is required."},
        )
    return user


async def require_attendee(
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> AuthenticatedUser:
    if user.role is not UserRole.ATTENDEE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "attendee_required", "message": "Attendee access is required."},
        )
    return user


async def require_attendee_owned_resource(
    attendee_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_attendee)],
) -> AuthenticatedUser:
    """Use on future attendee-private routes that include an attendee_id path value."""
    if user.id != attendee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ownership_required", "message": "You do not own this resource."},
        )
    return user
