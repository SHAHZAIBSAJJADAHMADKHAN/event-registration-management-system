"""Database access for application profiles."""

from uuid import UUID

from app.database.client import create_secret_client
from app.schemas.auth import AuthenticatedUser, UserRole
from app.core.config import Settings


class ProfileRepository:
    """Loads backend-authoritative role data after JWT verification."""

    def __init__(self, settings: Settings) -> None:
        self._client = create_secret_client(settings)

    def get_authenticated_user(self, user_id: UUID) -> AuthenticatedUser | None:
        response = (
            self._client.table("profiles")
            .select("id,full_name,role")
            .eq("id", str(user_id))
            .limit(1)
            .execute()
        )
        if not response.data:
            return None

        profile = response.data[0]
        return AuthenticatedUser(
            id=profile["id"],
            full_name=profile["full_name"],
            role=UserRole(profile["role"]),
        )
