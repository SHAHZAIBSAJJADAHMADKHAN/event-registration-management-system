from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.routes.admin_events import get_event_service
from app.core.errors import APIError
from app.dependencies.auth import require_admin, require_authenticated_user
from app.main import app
from app.schemas.auth import AuthenticatedUser, UserRole
from app.schemas.events import EventCreate, EventStatusTransition, EventUpdate
from app.services.discovery import EventDiscoveryService
from app.services.events import EventService


class InMemoryEventRepository:
    def __init__(self) -> None:
        self.events: dict[UUID, dict[str, object]] = {}
        self.active_counts: dict[UUID, int] = {}
        self.registration_counts: dict[UUID, int] = {}
        self.registrations: dict[UUID, UUID] = {}
        self.notifications: list[dict[str, UUID | None]] = []
        self.delete_failure = False

    def create(self, values: dict[str, object]) -> dict[str, object]:
        event_id = uuid4()
        now = datetime.now(timezone.utc).isoformat()
        event = {"id": str(event_id), "created_at": now, "updated_at": now, **values}
        self.events[event_id] = event
        return event

    def list_all(self) -> list[dict[str, object]]:
        return list(self.events.values())

    def get(self, event_id: UUID) -> dict[str, object] | None:
        return self.events.get(event_id)

    def update(self, event_id: UUID, values: dict[str, object]) -> dict[str, object] | None:
        event = self.events.get(event_id)
        if event is None:
            return None
        event.update(values)
        event["updated_at"] = datetime.now(timezone.utc).isoformat()
        return event

    def count_approved_registrations(self, event_id: UUID) -> int:
        return self.active_counts.get(event_id, 0)

    def count_registrations(self, event_id: UUID) -> int:
        return self.registration_counts.get(event_id, 0)

    def delete(self, event_id: UUID) -> bool:
        return self.events.pop(event_id, None) is not None

    def add_related_data(self, event_id: UUID) -> UUID:
        registration_id = uuid4()
        self.registrations[registration_id] = event_id
        self.notifications.extend([
            {"event_id": event_id, "registration_id": None},
            {"event_id": None, "registration_id": registration_id},
        ])
        return registration_id

    def delete_hard_atomic(self, event_id: UUID) -> bool:
        if self.delete_failure:
            raise RuntimeError("simulated database failure")
        registration_ids = {registration_id for registration_id, related_event_id in self.registrations.items() if related_event_id == event_id}
        self.notifications = [notification for notification in self.notifications if notification["event_id"] != event_id and notification["registration_id"] not in registration_ids]
        self.registrations = {registration_id: related_event_id for registration_id, related_event_id in self.registrations.items() if related_event_id != event_id}
        return self.events.pop(event_id, None) is not None

    def list_published_upcoming(self, now: datetime) -> list[dict[str, object]]:
        return [
            event
            for event in self.events.values()
            if event["status"] == "published"
            and datetime.fromisoformat(str(event["starts_at"])) > now
        ]

    def approved_registration_counts(self, event_ids: list[UUID]) -> dict[UUID, int]:
        return {event_id: self.active_counts.get(event_id, 0) for event_id in event_ids}


ADMIN = AuthenticatedUser(id=uuid4(), full_name="Admin", role=UserRole.ADMIN)
ATTENDEE = AuthenticatedUser(id=uuid4(), full_name="Attendee", role=UserRole.ATTENDEE)


def payload(**overrides: object) -> dict[str, object]:
    event = {
        "title": "Security workshop",
        "description": "A practical security workshop.",
        "starts_at": "2030-01-01T10:00:00Z",
        "ends_at": "2030-01-01T12:00:00Z",
        "location": "Nowshera Hall",
        "capacity": 25,
        "status": "draft",
    }
    event.update(overrides)
    return event


@pytest.fixture
def event_service() -> EventService:
    return EventService(InMemoryEventRepository())


@pytest.fixture
def admin_client(event_service: EventService):
    app.dependency_overrides[require_admin] = lambda: ADMIN
    app.dependency_overrides[get_event_service] = lambda: event_service
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_admin_creates_lists_gets_and_updates_event(admin_client: TestClient) -> None:
    created = admin_client.post("/api/admin/events", json=payload())
    assert created.status_code == 201
    event = created.json()
    assert event["status"] == "draft"
    assert event["ends_at"] == "2030-01-01T12:00:00Z"
    assert event["created_by"] == str(ADMIN.id)

    listed = admin_client.get("/api/admin/events")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    fetched = admin_client.get(f"/api/admin/events/{event['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == event["id"]

    updated = admin_client.patch(
        f"/api/admin/events/{event['id']}", json={"title": "Updated workshop", "capacity": 30}
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Updated workshop"
    assert updated.json()["capacity"] == 30


def test_admin_can_create_published_event_that_is_discoverable(
    admin_client: TestClient,
    event_service: EventService,
) -> None:
    response = admin_client.post(
        "/api/admin/events",
        json=payload(status="published", starts_at=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat(), ends_at=(datetime.now(timezone.utc) + timedelta(days=1, hours=2)).isoformat()),
    )
    assert response.status_code == 201

    discoverable = EventDiscoveryService(event_service._repository).list_upcoming()

    assert response.json()["status"] == "published"
    assert len(discoverable) == 1
    assert str(discoverable[0].id) == response.json()["id"]


def test_unauthenticated_and_attendee_requests_are_rejected(event_service: EventService) -> None:
    app.dependency_overrides[get_event_service] = lambda: event_service
    with TestClient(app) as client:
        unauthenticated = client.post("/api/admin/events", json=payload())
        unauthenticated_delete = client.delete(f"/api/admin/events/{uuid4()}")
    assert unauthenticated.status_code == 401
    assert unauthenticated_delete.status_code == 401
    app.dependency_overrides.clear()

    app.dependency_overrides[require_authenticated_user] = lambda: ATTENDEE
    app.dependency_overrides[get_event_service] = lambda: event_service
    with TestClient(app) as client:
        attendee_draft = client.post("/api/admin/events", json=payload(status="draft"))
        attendee_published = client.post("/api/admin/events", json=payload(status="published"))
        attendee_update = client.patch(f"/api/admin/events/{uuid4()}", json={"capacity": 10})
        attendee_delete = client.delete(f"/api/admin/events/{uuid4()}")
    app.dependency_overrides.clear()
    assert attendee_draft.status_code == 403
    assert attendee_published.status_code == 403
    assert attendee_update.status_code == 403
    assert attendee_delete.status_code == 403


@pytest.mark.parametrize(
    "invalid_payload",
    [
        payload(capacity=0),
        payload(status="invalid"),
        payload(status="completed"),
        payload(status="cancelled"),
        payload(status="published", starts_at="2000-01-01T10:00:00Z"),
        payload(starts_at="2030-01-01T10:00:00"),
        payload(ends_at="2030-01-01T10:00:00Z"),
        payload(ends_at="2030-01-01T09:00:00Z"),
    ],
)
def test_invalid_event_input_is_rejected(
    admin_client: TestClient, invalid_payload: dict[str, object]
) -> None:
    response = admin_client.post("/api/admin/events", json=invalid_payload)
    assert response.status_code == 422


def test_missing_event_and_invalid_transition_return_safe_errors(admin_client: TestClient) -> None:
    missing = admin_client.get(f"/api/admin/events/{uuid4()}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "event_not_found"

    created = admin_client.post("/api/admin/events", json=payload()).json()
    invalid = admin_client.patch(f"/api/admin/events/{created['id']}/status", json={"status": "completed"})
    assert invalid.status_code == 409
    assert invalid.json()["error"]["code"] == "invalid_event_transition"


def test_new_events_require_explicit_status_and_end_time(admin_client: TestClient) -> None:
    no_status = payload()
    no_status.pop("status")
    assert admin_client.post("/api/admin/events", json=no_status).status_code == 422

    no_end = payload()
    no_end.pop("ends_at")
    assert admin_client.post("/api/admin/events", json=no_end).status_code == 422


def test_event_updates_validate_resulting_start_and_end_times(admin_client: TestClient) -> None:
    created = admin_client.post("/api/admin/events", json=payload()).json()
    event_id = created["id"]
    event_path = f"/api/admin/events/{event_id}"

    valid_start = admin_client.patch(event_path, json={"starts_at": "2030-01-01T11:00:00Z"})
    assert valid_start.status_code == 200
    assert valid_start.json()["ends_at"] == "2030-01-01T12:00:00Z"

    valid_end = admin_client.patch(event_path, json={"ends_at": "2030-01-01T13:00:00Z"})
    assert valid_end.status_code == 200
    assert valid_end.json()["ends_at"] == "2030-01-01T13:00:00Z"

    invalid_start = admin_client.patch(event_path, json={"starts_at": "2030-01-01T13:00:00Z"})
    assert invalid_start.status_code == 422
    assert invalid_start.json()["error"]["code"] == "invalid_event_schedule"

    invalid_end = admin_client.patch(event_path, json={"ends_at": "2030-01-01T10:00:00Z"})
    assert invalid_end.status_code == 422


def test_legacy_event_without_end_time_is_readable(event_service: EventService) -> None:
    repository = event_service._repository
    event_id = uuid4()
    repository.events[event_id] = {
        "id": str(event_id), "title": "Legacy event", "description": "Existing event",
        "starts_at": "2030-01-01T10:00:00Z", "location": "Nowshera Hall", "capacity": 25,
        "status": "draft", "created_by": str(ADMIN.id),
        "created_at": "2030-01-01T09:00:00Z", "updated_at": "2030-01-01T09:00:00Z",
    }

    assert event_service.get(event_id).ends_at is None


def test_status_transitions_cancel_and_complete_are_terminal(admin_client: TestClient) -> None:
    draft = admin_client.post("/api/admin/events", json=payload()).json()
    cancelled = admin_client.patch(f"/api/admin/events/{draft['id']}/status", json={"status": "cancelled"})
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert admin_client.patch(
        f"/api/admin/events/{draft['id']}/status", json={"status": "published"}
    ).status_code == 409

    published = admin_client.post("/api/admin/events", json=payload()).json()
    assert admin_client.patch(
        f"/api/admin/events/{published['id']}/status", json={"status": "published"}
    ).status_code == 200
    completed = admin_client.patch(
        f"/api/admin/events/{published['id']}/status", json={"status": "completed"}
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert admin_client.patch(
        f"/api/admin/events/{published['id']}/status", json={"status": "cancelled"}
    ).status_code == 409


def test_capacity_cannot_be_reduced_below_active_registration_count(event_service: EventService) -> None:
    created = event_service.create(EventCreate.model_validate(payload(capacity=5)), ADMIN)
    repository = event_service._repository
    repository.active_counts[created.id] = 3

    with pytest.raises(APIError) as error:
        event_service.update(created.id, EventUpdate(capacity=2))
    assert error.value.status_code == 409
    assert error.value.code == "capacity_below_approved_registrations"


def test_admin_hard_deletes_draft_and_cancelled_events(admin_client: TestClient) -> None:
    draft = admin_client.post("/api/admin/events", json=payload()).json()
    deleted = admin_client.delete(f"/api/admin/events/{draft['id']}")
    assert deleted.status_code == 200
    assert deleted.json() == {"deleted": True}
    assert admin_client.get(f"/api/admin/events/{draft['id']}").status_code == 404

    cancelled = admin_client.post("/api/admin/events", json=payload()).json()
    assert admin_client.patch(f"/api/admin/events/{cancelled['id']}/status", json={"status": "cancelled"}).status_code == 200
    assert admin_client.delete(f"/api/admin/events/{cancelled['id']}").status_code == 200


def test_hard_delete_removes_related_data_for_all_event_states_and_preserves_unrelated_data(admin_client: TestClient, event_service: EventService) -> None:
    repository = event_service._repository
    unrelated_event = admin_client.post("/api/admin/events", json=payload()).json()
    unrelated_event_id = UUID(unrelated_event["id"])
    unrelated_registration = repository.add_related_data(unrelated_event_id)

    for lifecycle in ("draft", "published", "completed", "cancelled"):
        created = admin_client.post("/api/admin/events", json=payload(status="published" if lifecycle in {"published", "completed"} else "draft")).json()
        if lifecycle == "completed":
            assert admin_client.patch(f"/api/admin/events/{created['id']}/status", json={"status": "completed"}).status_code == 200
        if lifecycle == "cancelled":
            assert admin_client.patch(f"/api/admin/events/{created['id']}/status", json={"status": "cancelled"}).status_code == 200
        event_id = UUID(created["id"])
        related_registration = repository.add_related_data(event_id)
        assert admin_client.delete(f"/api/admin/events/{created['id']}").status_code == 200
        assert event_id not in repository.events
        assert related_registration not in repository.registrations
        assert all(notification["event_id"] != event_id and notification["registration_id"] != related_registration for notification in repository.notifications)

    assert unrelated_event_id in repository.events
    assert unrelated_registration in repository.registrations
    assert any(notification["registration_id"] == unrelated_registration for notification in repository.notifications)


def test_hard_delete_missing_and_rpc_failure_return_safe_errors(admin_client: TestClient, event_service: EventService) -> None:
    missing = admin_client.delete(f"/api/admin/events/{uuid4()}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "event_not_found"
    event = admin_client.post("/api/admin/events", json=payload()).json()
    event_service._repository.delete_failure = True
    failed = admin_client.delete(f"/api/admin/events/{event['id']}")
    assert failed.status_code == 503
    assert failed.json()["error"]["code"] == "event_delete_failed"
