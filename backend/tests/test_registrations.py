from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.routes.registrations import get_registration_service
from app.core.errors import APIError
from app.database.registrations import RegistrationDatabaseError
from app.dependencies.auth import require_attendee, require_authenticated_user
from app.main import app
from app.schemas.auth import AuthenticatedUser, UserRole
from app.services.registrations import RegistrationService


ATTENDEE_A = AuthenticatedUser(id=uuid4(), full_name="Attendee A", role=UserRole.ATTENDEE)
ATTENDEE_B = AuthenticatedUser(id=uuid4(), full_name="Attendee B", role=UserRole.ATTENDEE)
ADMIN = AuthenticatedUser(id=uuid4(), full_name="Admin", role=UserRole.ADMIN)


class InMemoryRegistrationRepository:
    def __init__(self) -> None:
        self.event_id = uuid4()
        self.events = {
            self.event_id: {
                "id": str(self.event_id),
                "title": "Future workshop",
                "starts_at": "2030-01-01T10:00:00Z",
                "location": "Nowshera Hall",
                "status": "published",
            }
        }
        self.registrations: dict[UUID, dict[str, object]] = {}
        self.failures: dict[UUID, str] = {}
        self.capacity = 2
        self.atomic_calls = 0

    def create_atomic(self, event_id: UUID, attendee_id: UUID) -> dict[str, object]:
        self.atomic_calls += 1
        if event_id in self.failures:
            raise RegistrationDatabaseError("P0001", self.failures[event_id])
        if event_id not in self.events:
            raise RegistrationDatabaseError("P0001", "Event not found")
        if any(
            row["event_id"] == str(event_id)
            and row["attendee_id"] == str(attendee_id)
            and row["status"] == "active"
            for row in self.registrations.values()
        ):
            raise RegistrationDatabaseError("P0001", "An active registration already exists for this event")
        if self.active_count(event_id) >= self.capacity:
            raise RegistrationDatabaseError("P0001", "Event capacity has been reached")
        registration_id = uuid4()
        now = datetime.now(timezone.utc).isoformat()
        row = {
            "id": str(registration_id),
            "event_id": str(event_id),
            "attendee_id": str(attendee_id),
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        self.registrations[registration_id] = row
        return row

    def get_owned(self, registration_id: UUID, attendee_id: UUID):
        row = self.registrations.get(registration_id)
        if row and row["attendee_id"] == str(attendee_id):
            return row
        return None

    def list_owned(self, attendee_id: UUID):
        return [
            row for row in self.registrations.values()
            if row["attendee_id"] == str(attendee_id)
        ]

    def cancel_owned_active(self, registration_id: UUID, attendee_id: UUID):
        row = self.get_owned(registration_id, attendee_id)
        if row is None or row["status"] != "active":
            return None
        row["status"] = "cancelled"
        row["updated_at"] = datetime.now(timezone.utc).isoformat()
        return row

    def get_events(self, event_ids: list[UUID]):
        return {event_id: self.events[event_id] for event_id in event_ids if event_id in self.events}

    def active_count(self, event_id: UUID) -> int:
        return sum(
            row["event_id"] == str(event_id) and row["status"] == "active"
            for row in self.registrations.values()
        )


@pytest.fixture
def registration_service() -> RegistrationService:
    return RegistrationService(InMemoryRegistrationRepository())


@pytest.fixture
def attendee_client(registration_service: RegistrationService):
    app.dependency_overrides[require_attendee] = lambda: ATTENDEE_A
    app.dependency_overrides[get_registration_service] = lambda: registration_service
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_successful_registration_and_my_registration_history(
    attendee_client: TestClient, registration_service: RegistrationService
) -> None:
    event_id = registration_service._repository.event_id
    created = attendee_client.post(f"/events/{event_id}/registrations")
    assert created.status_code == 201
    registration = created.json()
    assert registration["status"] == "active"
    assert registration["event"]["title"] == "Future workshop"
    assert registration_service._repository.atomic_calls == 1

    mine = attendee_client.get("/me/registrations")
    assert mine.status_code == 200
    assert [row["id"] for row in mine.json()] == [registration["id"]]
    assert attendee_client.get(f"/me/registrations/{registration['id']}").status_code == 200


def test_duplicate_and_full_registration_are_rejected(
    attendee_client: TestClient, registration_service: RegistrationService
) -> None:
    event_id = registration_service._repository.event_id
    assert attendee_client.post(f"/events/{event_id}/registrations").status_code == 201
    duplicate = attendee_client.post(f"/events/{event_id}/registrations")
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "duplicate_registration"

    registration_service._repository.registrations.clear()
    registration_service._repository.capacity = 1
    registration_service._repository.create_atomic(event_id, ATTENDEE_B.id)
    full = attendee_client.post(f"/events/{event_id}/registrations")
    assert full.status_code == 409
    assert full.json()["error"]["code"] == "event_full"


@pytest.mark.parametrize(
    "failure",
    [
        "Registration is closed for this event",
        "Registration is closed for past events",
        "Event capacity has been reached",
        "Event not found",
    ],
)
def test_ineligible_events_are_rejected_by_atomic_foundation(
    attendee_client: TestClient, registration_service: RegistrationService, failure: str
) -> None:
    event_id = registration_service._repository.event_id
    registration_service._repository.failures[event_id] = failure

    response = attendee_client.post(f"/events/{event_id}/registrations")
    assert response.status_code in {404, 409}
    assert response.json()["error"]["code"] in {"event_not_eligible", "event_full", "event_not_found"}


def test_cancellation_preserves_history_releases_capacity_and_cannot_repeat(
    attendee_client: TestClient, registration_service: RegistrationService
) -> None:
    event_id = registration_service._repository.event_id
    created = attendee_client.post(f"/events/{event_id}/registrations").json()
    assert registration_service._repository.active_count(event_id) == 1

    cancelled = attendee_client.patch(f"/me/registrations/{created['id']}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert registration_service._repository.active_count(event_id) == 0

    repeated = attendee_client.patch(f"/me/registrations/{created['id']}/cancel")
    assert repeated.status_code == 409
    assert repeated.json()["error"]["code"] == "registration_already_cancelled"

    replacement = attendee_client.post(f"/events/{event_id}/registrations")
    assert replacement.status_code == 201
    assert registration_service._repository.active_count(event_id) == 1


def test_attendee_cannot_read_or_cancel_another_attendees_registration(
    attendee_client: TestClient, registration_service: RegistrationService
) -> None:
    event_id = registration_service._repository.event_id
    other = registration_service._repository.create_atomic(event_id, ATTENDEE_B.id)

    detail = attendee_client.get(f"/me/registrations/{other['id']}")
    cancel = attendee_client.patch(f"/me/registrations/{other['id']}/cancel")
    assert detail.status_code == 404
    assert cancel.status_code == 404
    assert registration_service._repository.get_owned(UUID(other["id"]), ATTENDEE_B.id)["status"] == "active"


def test_unauthenticated_and_non_attendee_registration_access_is_rejected(
    registration_service: RegistrationService,
) -> None:
    event_id = registration_service._repository.event_id
    app.dependency_overrides[get_registration_service] = lambda: registration_service
    with TestClient(app) as client:
        unauthenticated = client.post(f"/events/{event_id}/registrations")
    app.dependency_overrides.clear()
    assert unauthenticated.status_code == 401

    app.dependency_overrides[require_authenticated_user] = lambda: ADMIN
    app.dependency_overrides[get_registration_service] = lambda: registration_service
    with TestClient(app) as client:
        admin = client.post(f"/events/{event_id}/registrations")
    app.dependency_overrides.clear()
    assert admin.status_code == 403
