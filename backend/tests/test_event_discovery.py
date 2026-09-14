from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.routes.discovery import get_event_discovery_service
from app.dependencies.auth import require_attendee, require_authenticated_user
from app.main import app
from app.schemas.auth import AuthenticatedUser, UserRole
from app.services.discovery import EventDiscoveryService


ATTENDEE = AuthenticatedUser(id=uuid4(), full_name="Attendee", role=UserRole.ATTENDEE)
ADMIN = AuthenticatedUser(id=uuid4(), full_name="Admin", role=UserRole.ADMIN)


def event(status: str, starts_at: datetime, capacity: int = 10) -> dict[str, object]:
    return {
        "id": str(uuid4()),
        "title": f"{status} event",
        "description": "Event description",
        "starts_at": starts_at.isoformat(),
        "location": "Nowshera Hall",
        "capacity": capacity,
        "status": status,
    }


class InMemoryDiscoveryRepository:
    def __init__(self, events: list[dict[str, object]], counts: dict[UUID, int]) -> None:
        self.events = events
        self.counts = counts

    def list_published_upcoming(self, now: datetime) -> list[dict[str, object]]:
        return sorted(
            [
                item
                for item in self.events
                if item["status"] == "published"
                and datetime.fromisoformat(str(item["starts_at"])) > now
            ],
            key=lambda item: str(item["starts_at"]),
        )

    def get_published_upcoming(self, event_id: UUID, now: datetime):
        for item in self.list_published_upcoming(now):
            if UUID(str(item["id"])) == event_id:
                return item
        return None

    def approved_registration_counts(self, event_ids: list[UUID]) -> dict[UUID, int]:
        return {event_id: self.counts.get(event_id, 0) for event_id in event_ids}


@pytest.fixture
def discovery_service() -> EventDiscoveryService:
    now = datetime.now(timezone.utc)
    published_future = event("published", now + timedelta(days=1), capacity=5)
    draft = event("draft", now + timedelta(days=2))
    cancelled = event("cancelled", now + timedelta(days=3))
    completed = event("completed", now + timedelta(days=4))
    past_published = event("published", now - timedelta(days=1))
    published_future_id = UUID(str(published_future["id"]))
    return EventDiscoveryService(
        InMemoryDiscoveryRepository(
            [draft, cancelled, completed, past_published, published_future],
            {published_future_id: 2},
        )
    )


@pytest.fixture
def attendee_client(discovery_service: EventDiscoveryService):
    app.dependency_overrides[require_attendee] = lambda: ATTENDEE
    app.dependency_overrides[get_event_discovery_service] = lambda: discovery_service
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_only_published_future_events_appear(attendee_client: TestClient) -> None:
    response = attendee_client.get("/api/events")

    assert response.status_code == 200
    events = response.json()
    assert len(events) == 1
    assert events[0]["status"] == "published"
    assert events[0]["active_registration_count"] == 2
    assert events[0]["remaining_availability"] == 3


def test_cancelled_registration_does_not_consume_capacity(
    discovery_service: EventDiscoveryService,
) -> None:
    result = discovery_service.list_upcoming()[0]

    assert result.capacity == 5
    assert result.active_registration_count == 2
    assert result.remaining_availability == 3


def test_remaining_availability_never_becomes_negative() -> None:
    now = datetime.now(timezone.utc)
    published = event("published", now + timedelta(days=1), capacity=1)
    event_id = UUID(str(published["id"]))
    service = EventDiscoveryService(InMemoryDiscoveryRepository([published], {event_id: 2}))

    assert service.list_upcoming()[0].remaining_availability == 0


def test_attendee_can_open_discoverable_event(attendee_client: TestClient) -> None:
    listed = attendee_client.get("/api/events").json()
    detail = attendee_client.get(f"/api/events/{listed[0]['id']}")

    assert detail.status_code == 200
    assert detail.json()["remaining_availability"] == 3
    assert "created_by" not in detail.json()
    assert "created_at" not in detail.json()


def test_non_discoverable_detail_returns_not_found(
    attendee_client: TestClient, discovery_service: EventDiscoveryService
) -> None:
    hidden_id = next(
        UUID(str(item["id"]))
        for item in discovery_service._repository.events
        if item["status"] == "draft"
    )

    response = attendee_client.get(f"/api/events/{hidden_id}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "event_not_found"


def test_unauthenticated_and_admin_discovery_access_are_rejected(
    discovery_service: EventDiscoveryService,
) -> None:
    app.dependency_overrides[get_event_discovery_service] = lambda: discovery_service
    with TestClient(app) as client:
        unauthenticated = client.get("/api/events")
    app.dependency_overrides.clear()
    assert unauthenticated.status_code == 401

    app.dependency_overrides[require_authenticated_user] = lambda: ADMIN
    app.dependency_overrides[get_event_discovery_service] = lambda: discovery_service
    with TestClient(app) as client:
        admin = client.get("/api/events")
    app.dependency_overrides.clear()
    assert admin.status_code == 403
