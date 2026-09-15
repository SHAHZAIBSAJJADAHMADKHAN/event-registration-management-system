from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from app.core.errors import APIError
from app.database.registrations import RegistrationDatabaseError
from app.schemas.auth import AuthenticatedUser, UserRole
from app.services.admin_operations import AdminOperationsService
from app.services.admin_registrations import AdminRegistrationService
from app.services.discovery import EventDiscoveryService
from app.services.events import EventService
from app.services.registrations import RegistrationService


NOW = datetime.now(timezone.utc)
ATTENDEE = AuthenticatedUser(id=uuid4(), full_name="Attendee", role=UserRole.ATTENDEE)


def make_event(status: str, ends_at: datetime | None) -> dict[str, object]:
    event_id = uuid4()
    starts_at = (
        ends_at - timedelta(hours=1)
        if ends_at is not None and ends_at <= NOW
        else NOW + timedelta(days=1)
    )
    return {
        "id": str(event_id),
        "title": f"{status.title()} event",
        "description": "Lifecycle test event",
        "starts_at": starts_at.isoformat(),
        "ends_at": ends_at.isoformat() if ends_at is not None else None,
        "location": "Nowshera Hall",
        "capacity": 5,
        "status": status,
        "created_by": str(uuid4()),
        "created_at": NOW.isoformat(),
        "updated_at": NOW.isoformat(),
    }


class InMemoryLifecycle:
    def __init__(self, events: dict[UUID, dict[str, object]]) -> None:
        self.events = events
        self.calls = 0

    def reconcile_overdue_events(self) -> int:
        self.calls += 1
        completed = 0
        for event in self.events.values():
            ends_at = event.get("ends_at")
            if (
                event["status"] == "published"
                and ends_at is not None
                and datetime.fromisoformat(str(ends_at)) <= NOW
            ):
                event["status"] = "completed"
                completed += 1
        return completed


class InMemoryLifecycleRepository:
    def __init__(self) -> None:
        self.events: dict[UUID, dict[str, object]] = {}
        self.registrations: list[dict[str, object]] = []

    def add(self, status: str, ends_at: datetime | None) -> UUID:
        row = make_event(status, ends_at)
        event_id = UUID(str(row["id"]))
        self.events[event_id] = row
        return event_id

    def list_all(self) -> list[dict[str, object]]:
        return list(self.events.values())

    def get(self, event_id: UUID) -> dict[str, object] | None:
        return self.events.get(event_id)

    def get_event(self, event_id: UUID) -> dict[str, object] | None:
        return self.get(event_id)

    def list_published_upcoming(self, now: datetime) -> list[dict[str, object]]:
        return [
            event
            for event in self.events.values()
            if event["status"] == "published"
            and datetime.fromisoformat(str(event["starts_at"])) > now
        ]

    def get_published_upcoming(self, event_id: UUID, now: datetime) -> dict[str, object] | None:
        return next(
            (event for event in self.list_published_upcoming(now) if UUID(str(event["id"])) == event_id),
            None,
        )

    def approved_registration_counts(self, event_ids: list[UUID]) -> dict[UUID, int]:
        return {
            event_id: sum(
                row["event_id"] == str(event_id) and row["status"] == "approved"
                for row in self.registrations
            )
            for event_id in event_ids
        }

    def list_owned(self, attendee_id: UUID) -> list[dict[str, object]]:
        return [row for row in self.registrations if row["attendee_id"] == str(attendee_id)]

    def get_owned(self, registration_id: UUID, attendee_id: UUID) -> dict[str, object] | None:
        return next(
            (
                row
                for row in self.registrations
                if row["id"] == str(registration_id) and row["attendee_id"] == str(attendee_id)
            ),
            None,
        )

    def get_events(self, event_ids: list[UUID]) -> dict[UUID, dict[str, object]]:
        return {event_id: self.events[event_id] for event_id in event_ids if event_id in self.events}

    def list_events(self) -> list[dict[str, object]]:
        return self.list_all()

    def list_registrations(self) -> list[dict[str, object]]:
        return self.registrations

    def list_event_registrations(self, event_id: UUID, registration_status=None) -> list[dict[str, object]]:
        rows = [row for row in self.registrations if row["event_id"] == str(event_id)]
        return rows if registration_status is None else [row for row in rows if row["status"] == registration_status.value]

    def profiles(self, attendee_ids: list[UUID]) -> dict[UUID, dict[str, object]]:
        return {attendee_id: {"full_name": "Attendee"} for attendee_id in attendee_ids}

    def attendee_email(self, attendee_id: UUID) -> str:
        return "attendee@example.test"

    def approve_atomic(self, registration_id: UUID) -> dict[str, object]:
        registration = next(row for row in self.registrations if row["id"] == str(registration_id))
        event = self.events[UUID(str(registration["event_id"]))]
        if event["status"] != "published" or (
            event["ends_at"] is not None and datetime.fromisoformat(str(event["ends_at"])) <= NOW
        ):
            raise RegistrationDatabaseError("P0001", "Registration is closed for this event")
        registration["status"] = "approved"
        return registration


class Notifications:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def create(self, *args: object) -> None:
        self.calls.append(args)


def test_reconciliation_completes_only_ended_published_events_and_is_idempotent() -> None:
    repository = InMemoryLifecycleRepository()
    future = repository.add("published", NOW + timedelta(hours=1))
    overdue = repository.add("published", NOW)
    draft = repository.add("draft", NOW - timedelta(hours=1))
    cancelled = repository.add("cancelled", NOW - timedelta(hours=1))
    completed = repository.add("completed", NOW - timedelta(hours=1))
    legacy = repository.add("published", None)
    lifecycle = InMemoryLifecycle(repository.events)

    assert lifecycle.reconcile_overdue_events() == 1
    assert lifecycle.reconcile_overdue_events() == 0
    assert repository.events[future]["status"] == "published"
    assert repository.events[overdue]["status"] == "completed"
    assert repository.events[draft]["status"] == "draft"
    assert repository.events[cancelled]["status"] == "cancelled"
    assert repository.events[completed]["status"] == "completed"
    assert repository.events[legacy]["status"] == "published"


def test_reconciliation_preserves_registration_rows_and_capacity_calculations() -> None:
    repository = InMemoryLifecycleRepository()
    future = repository.add("published", NOW + timedelta(hours=1))
    overdue = repository.add("published", NOW - timedelta(hours=1))
    repository.registrations = [
        {"id": str(uuid4()), "event_id": str(future), "attendee_id": str(ATTENDEE.id), "status": "approved", "created_at": NOW.isoformat(), "updated_at": NOW.isoformat()},
        {"id": str(uuid4()), "event_id": str(overdue), "attendee_id": str(ATTENDEE.id), "status": "pending", "created_at": NOW.isoformat(), "updated_at": NOW.isoformat()},
    ]
    before = [dict(row) for row in repository.registrations]
    lifecycle = InMemoryLifecycle(repository.events)

    assert lifecycle.reconcile_overdue_events() == 1
    discovery = EventDiscoveryService(repository, lifecycle).list_upcoming()

    assert repository.registrations == before
    assert discovery[0].id == future
    assert discovery[0].remaining_availability == 4


def test_reconciled_read_paths_return_completed_status_and_hide_overdue_discovery() -> None:
    repository = InMemoryLifecycleRepository()
    overdue = repository.add("published", NOW - timedelta(hours=1))
    registration_id = uuid4()
    repository.registrations = [{
        "id": str(registration_id), "event_id": str(overdue), "attendee_id": str(ATTENDEE.id),
        "status": "approved", "created_at": NOW.isoformat(), "updated_at": NOW.isoformat(),
    }]
    lifecycle = InMemoryLifecycle(repository.events)

    assert EventService(repository, lifecycle).list_all()[0].status == "completed"
    assert EventDiscoveryService(repository, lifecycle).list_upcoming() == []
    mine = RegistrationService(repository, lifecycle=lifecycle).list_mine(ATTENDEE)
    assert mine[0].event.status == "completed"
    operations = AdminOperationsService(repository, lifecycle)
    assert operations.event_report()[0].status == "completed"
    assert operations.detailed_event_report(overdue).status == "completed"


def test_approval_after_event_end_is_blocked_without_notification_or_registration_change() -> None:
    repository = InMemoryLifecycleRepository()
    overdue = repository.add("published", NOW - timedelta(hours=1))
    registration_id = uuid4()
    repository.registrations = [{
        "id": str(registration_id), "event_id": str(overdue), "attendee_id": str(ATTENDEE.id),
        "status": "pending", "created_at": NOW.isoformat(), "updated_at": NOW.isoformat(),
    }]
    notifications = Notifications()
    service = AdminRegistrationService(repository, notifications, InMemoryLifecycle(repository.events))

    with pytest.raises(APIError) as error:
        service.approve(registration_id)

    assert "Registration is not available" in str(error.value)
    assert repository.registrations[0]["status"] == "pending"
    assert notifications.calls == []


def test_completion_migration_has_authoritative_conditions_and_no_cron() -> None:
    migration = (
        Path(__file__).resolve().parents[2]
        / "supabase"
        / "migrations"
        / "20260915000300_automatic_event_completion_foundation.sql"
    ).read_text(encoding="utf-8").lower()

    assert "create or replace function public.complete_overdue_events()" in migration
    assert "status = 'published'" in migration
    assert "ends_at is not null" in migration
    assert "ends_at <= now()" in migration
    assert "set status = 'completed'" in migration
    assert "security definer" in migration
    assert "auth.role() <> 'service_role'" in migration
    assert "selected_event.ends_at is not null and selected_event.ends_at <= now()" in migration
    assert "pg_cron" not in migration
    assert "cron.schedule" not in migration
