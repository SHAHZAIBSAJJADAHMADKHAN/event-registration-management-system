from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.routes.admin_operations import _attendee_csv, get_admin_operations_service
from app.dependencies.auth import require_admin, require_authenticated_user
from app.main import app
from app.schemas.auth import AuthenticatedUser, UserRole
from app.schemas.admin_operations import AdminAttendeeRegistration
from app.schemas.foundation import RegistrationStatus
from app.services.admin_operations import AdminOperationsService


ADMIN = AuthenticatedUser(id=uuid4(), full_name="Admin", role=UserRole.ADMIN)
ATTENDEE = AuthenticatedUser(id=uuid4(), full_name="Attendee", role=UserRole.ATTENDEE)


class InMemoryAdminOperationsRepository:
    def __init__(self) -> None:
        self.event_id = uuid4()
        self.other_event_id = uuid4()
        self.active_attendee_id = uuid4()
        self.cancelled_attendee_id = uuid4()
        self.events = {
            self.event_id: {"id": str(self.event_id), "title": "Town Hall", "starts_at": "2030-01-01T10:00:00+00:00", "location": "Civic Centre", "status": "published", "capacity": 3},
            self.other_event_id: {"id": str(self.other_event_id), "title": "Workshop", "starts_at": "2030-02-01T10:00:00+00:00", "location": "Library", "status": "draft", "capacity": 1},
        }
        now = datetime(2030, 1, 1, 10, 0, tzinfo=timezone.utc).isoformat()
        self.registrations = [
            {
                "id": str(uuid4()), "event_id": str(self.event_id),
                "attendee_id": str(self.active_attendee_id), "status": "active", "created_at": now,
            },
            {
                "id": str(uuid4()), "event_id": str(self.event_id),
                "attendee_id": str(self.cancelled_attendee_id), "status": "cancelled", "created_at": now,
            },
            {
                "id": str(uuid4()), "event_id": str(self.other_event_id),
                "attendee_id": str(uuid4()), "status": "active", "created_at": now,
            },
        ]
        self.profile_data = {
            self.active_attendee_id: {"id": str(self.active_attendee_id), "full_name": "Alice Attendee"},
            self.cancelled_attendee_id: {"id": str(self.cancelled_attendee_id), "full_name": "Bob Cancelled"},
        }
        self.emails = {
            self.active_attendee_id: "alice@example.test",
            self.cancelled_attendee_id: "bob@example.test",
        }

    def get_event(self, event_id: UUID):
        return self.events.get(event_id)

    def list_event_registrations(self, event_id: UUID, registration_status=None):
        rows = [row for row in self.registrations if row["event_id"] == str(event_id)]
        if registration_status is not None:
            rows = [row for row in rows if row["status"] == registration_status.value]
        return rows

    def profiles(self, attendee_ids: list[UUID]):
        return {attendee_id: self.profile_data[attendee_id] for attendee_id in attendee_ids if attendee_id in self.profile_data}

    def attendee_email(self, attendee_id: UUID):
        return self.emails.get(attendee_id)

    def list_events(self):
        return list(self.events.values())

    def list_registrations(self):
        return self.registrations


@pytest.fixture
def operations_service() -> AdminOperationsService:
    return AdminOperationsService(InMemoryAdminOperationsRepository())


@pytest.fixture
def admin_client(operations_service: AdminOperationsService):
    app.dependency_overrides[require_admin] = lambda: ADMIN
    app.dependency_overrides[get_admin_operations_service] = lambda: operations_service
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_admin_attendee_list_filters_and_search(admin_client: TestClient, operations_service) -> None:
    event_id = operations_service._repository.event_id
    response = admin_client.get(f"/admin/events/{event_id}/attendees")
    assert response.status_code == 200
    assert {row["registration_status"] for row in response.json()} == {"active", "cancelled"}
    assert response.json()[0]["attendee_email"] == "alice@example.test"

    active = admin_client.get(f"/admin/events/{event_id}/attendees?status=active")
    assert active.status_code == 200
    assert [row["attendee_name"] for row in active.json()] == ["Alice Attendee"]

    searched = admin_client.get(f"/admin/events/{event_id}/attendees?search=bob%40example.test")
    assert searched.status_code == 200
    assert [row["attendee_name"] for row in searched.json()] == ["Bob Cancelled"]


def test_dashboard_summary_and_event_totals_use_active_capacity_only(
    admin_client: TestClient, operations_service
) -> None:
    event_id = operations_service._repository.event_id
    dashboard = admin_client.get("/admin/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json() == {
        "total_events": 2, "total_registrations": 3,
        "active_registrations": 2, "available_capacity": 2,
    }
    summary = admin_client.get(f"/admin/events/{event_id}/summary")
    assert summary.status_code == 200
    assert summary.json()["active_registrations"] == 1
    assert summary.json()["cancelled_registrations"] == 1
    assert summary.json()["remaining_availability"] == 2


def test_event_report_includes_operational_capacity_and_status(
    admin_client: TestClient, operations_service
) -> None:
    response = admin_client.get("/admin/reports/events")
    assert response.status_code == 200
    town_hall = next(row for row in response.json() if row["event_title"] == "Town Hall")
    assert town_hall == {
        "event_id": str(operations_service._repository.event_id), "event_title": "Town Hall",
        "starts_at": "2030-01-01T10:00:00Z", "location": "Civic Centre", "status": "published",
        "capacity": 3, "active_registrations": 1, "cancelled_registrations": 1,
        "remaining_availability": 2,
    }


def test_check_in_and_csv_export_are_practical_and_safe(
    admin_client: TestClient, operations_service
) -> None:
    event_id = operations_service._repository.event_id
    check_in = admin_client.get(f"/admin/events/{event_id}/check-in")
    assert check_in.status_code == 200
    assert [row["registration_status"] for row in check_in.json()] == ["active"]

    csv_export = admin_client.get(f"/admin/events/{event_id}/attendees/export.csv")
    assert csv_export.status_code == 200
    assert csv_export.headers["content-type"].startswith("text/csv")
    assert f'filename="event-{event_id}-attendees.csv"' in csv_export.headers["content-disposition"]
    assert "Registration ID,Registration Status,Registered At" in csv_export.text
    assert "alice@example.test" in csv_export.text


def test_missing_event_and_unauthorized_access_are_rejected(
    operations_service: AdminOperationsService,
) -> None:
    event_id = operations_service._repository.event_id
    app.dependency_overrides[get_admin_operations_service] = lambda: operations_service
    with TestClient(app) as client:
        unauthenticated = client.get("/admin/dashboard")
        missing = client.get(f"/admin/events/{uuid4()}/attendees")
    assert unauthenticated.status_code == 401
    assert missing.status_code == 401
    app.dependency_overrides.clear()

    app.dependency_overrides[require_admin] = lambda: ADMIN
    app.dependency_overrides[get_admin_operations_service] = lambda: operations_service
    with TestClient(app) as client:
        missing = client.get(f"/admin/events/{uuid4()}/attendees")
    app.dependency_overrides.clear()
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "event_not_found"


def test_attendee_is_denied_operational_data(operations_service: AdminOperationsService) -> None:
    event_id = operations_service._repository.event_id
    app.dependency_overrides[require_authenticated_user] = lambda: ATTENDEE
    app.dependency_overrides[get_admin_operations_service] = lambda: operations_service
    with TestClient(app) as client:
        responses = [
            client.get(f"/admin/events/{event_id}/attendees"),
            client.get("/admin/dashboard"),
            client.get("/admin/reports/events"),
            client.get(f"/admin/events/{event_id}/check-in"),
            client.get(f"/admin/events/{event_id}/attendees/export.csv"),
        ]
    app.dependency_overrides.clear()
    assert all(response.status_code == 403 for response in responses)


def test_csv_neutralizes_spreadsheet_formula_cells() -> None:
    event_id = uuid4()
    row = AdminAttendeeRegistration(
        registration_id=uuid4(), registration_status=RegistrationStatus.ACTIVE,
        registered_at=datetime(2030, 1, 1, tzinfo=timezone.utc), attendee_id=uuid4(),
        attendee_name="=unsafe", attendee_email="person@example.test",
        event_id=event_id, event_title="Town Hall",
    )
    assert "'=unsafe" in _attendee_csv([row])
