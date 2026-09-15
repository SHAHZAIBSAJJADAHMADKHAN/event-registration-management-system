"""Centralized reconciliation with the database-owned event lifecycle."""

from app.database.lifecycle import EventLifecycleRepository


class EventLifecycleService:
    def __init__(self, repository: EventLifecycleRepository) -> None:
        self._repository = repository

    def reconcile_overdue_events(self) -> int:
        return self._repository.complete_overdue_events()
