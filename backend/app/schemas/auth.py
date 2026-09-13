"""Authentication and authorization schemas."""

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class UserRole(StrEnum):
    ADMIN = "admin"
    ATTENDEE = "attendee"


class AuthenticatedUser(BaseModel):
    """Identity resolved from a verified JWT and the authoritative profile row."""

    id: UUID
    full_name: str
    role: UserRole


class CurrentUserResponse(BaseModel):
    id: UUID
    full_name: str
    role: UserRole
