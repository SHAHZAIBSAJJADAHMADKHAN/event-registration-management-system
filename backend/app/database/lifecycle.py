"""Trusted access to authoritative event lifecycle database functions."""

from app.core.config import Settings
from app.database.client import create_secret_client


class EventLifecycleRepository:
    def __init__(self, settings: Settings) -> None:
        self._client = create_secret_client(settings)

    def complete_overdue_events(self) -> int:
        response = self._client.rpc("complete_overdue_events").execute()
        return int(response.data or 0)
