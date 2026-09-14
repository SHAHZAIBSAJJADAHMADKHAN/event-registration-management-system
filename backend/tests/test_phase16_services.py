from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.core.errors import APIError
from app.database.registrations import RegistrationDatabaseError
from app.schemas.auth import AuthenticatedUser, UserRole
from app.services.admin_registrations import AdminRegistrationService
from app.services.notifications import NotificationService
from app.services.registrations import RegistrationService


ATTENDEE = AuthenticatedUser(id=uuid4(), full_name="Attendee", role=UserRole.ATTENDEE)
ADMIN_A = uuid4()
ADMIN_B = uuid4()


class Notifications:
    def __init__(self): self.rows = []
    def create(self, *args): self.rows.append(args)


class RegistrationRepo:
    def __init__(self):
        self.event_id, self.registration_id = uuid4(), uuid4()
        self.row = {"id": str(self.registration_id), "event_id": str(self.event_id), "attendee_id": str(ATTENDEE.id), "status": "pending", "created_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat()}
        self.fail: str | None = None
    def create_request_atomic(self, *_):
        if self.fail: raise RegistrationDatabaseError("P0001", self.fail)
        return self.row
    def get_events(self, _): return {self.event_id: {"id": str(self.event_id), "title": "Workshop", "starts_at": "2030-01-01T10:00:00Z", "location": "Hall", "status": "published"}}
    def admin_ids(self): return [ADMIN_A, ADMIN_B]
    def get_open_owned_for_event(self, event_id, attendee_id): return {"id": str(self.registration_id), "status": self.row["status"]} if event_id == self.event_id and attendee_id == ATTENDEE.id and self.row["status"] in {"pending", "approved"} else None
    def list_owned(self, _): return [self.row]
    def get_owned(self, registration_id, attendee_id): return self.row if registration_id == self.registration_id and attendee_id == ATTENDEE.id else None
    def cancel_owned_open(self, *_):
        if self.row["status"] not in {"pending", "approved"}: return None
        self.row["status"] = "cancelled"; return self.row
    def approve_atomic(self, _):
        if self.fail: raise RegistrationDatabaseError("P0001", self.fail)
        if self.row["status"] != "pending": raise RegistrationDatabaseError("P0001", "Registration request is no longer pending")
        self.row["status"] = "approved"; return self.row
    def reject_atomic(self, _):
        if self.fail: raise RegistrationDatabaseError("P0001", self.fail)
        if self.row["status"] != "pending": raise RegistrationDatabaseError("P0001", "Registration request is no longer pending")
        self.row["status"] = "rejected"; return self.row
    def list_all(self, status, event_id): return [self.row] if (status in (None, self.row["status"]) and event_id in (None, self.event_id)) else []
    def profiles(self, _): return {ATTENDEE.id: {"full_name": "Attendee"}}
    def attendee_email(self, _): return "attendee@example.test"


def test_pending_request_notifies_attendee_and_each_server_resolved_admin():
    repo, notifications = RegistrationRepo(), Notifications()
    result = RegistrationService(repo, notifications).create(repo.event_id, ATTENDEE)
    assert result.status == "pending"
    assert [row[1] for row in notifications.rows] == ["registration_request_submitted", "new_registration_request", "new_registration_request"]
    assert {notifications.rows[1][0], notifications.rows[2][0]} == {ADMIN_A, ADMIN_B}


@pytest.mark.parametrize("status", ["pending", "approved", "rejected", "cancelled"])
def test_current_registration_state_only_exposes_open_statuses(status):
    repo = RegistrationRepo(); repo.row["status"] = status
    state = RegistrationService(repo).current_for_event(repo.event_id, ATTENDEE)
    assert state.status == (status if status in {"pending", "approved"} else None)


def test_duplicate_and_full_request_errors_are_safe():
    repo = RegistrationRepo(); repo.fail = "An open registration request already exists for this event"
    with pytest.raises(APIError) as duplicate: RegistrationService(repo).create(repo.event_id, ATTENDEE)
    assert duplicate.value.code == "duplicate_registration"
    repo.fail = "Event capacity has been reached"
    with pytest.raises(APIError) as full: RegistrationService(repo).create(repo.event_id, ATTENDEE)
    assert full.value.code == "event_full"


def test_pending_and_approved_cancellation_are_allowed_but_rejected_is_not():
    repo = RegistrationRepo(); service = RegistrationService(repo)
    assert service.cancel(repo.registration_id, ATTENDEE).status == "cancelled"
    repo.row["status"] = "approved"
    assert service.cancel(repo.registration_id, ATTENDEE).status == "cancelled"
    repo.row["status"] = "rejected"
    with pytest.raises(APIError) as error: service.cancel(repo.registration_id, ATTENDEE)
    assert error.value.code == "registration_not_cancellable"


def test_approval_and_rejection_notify_only_after_successful_atomic_transition():
    repo, notifications = RegistrationRepo(), Notifications()
    admin = AdminRegistrationService(repo, notifications)
    assert admin.approve(repo.registration_id)["status"] == "approved"
    assert notifications.rows[-1][1] == "registration_approved"
    repo.row["status"] = "pending"
    assert admin.reject(repo.registration_id)["status"] == "rejected"
    assert notifications.rows[-1][1] == "registration_rejected"
    before = len(notifications.rows); repo.fail = "Event capacity has been reached"
    with pytest.raises(APIError): admin.approve(repo.registration_id)
    assert len(notifications.rows) == before


def test_admin_request_list_contains_only_operational_fields_and_filters():
    repo = RegistrationRepo()
    rows = AdminRegistrationService(repo, Notifications()).list_requests("pending", repo.event_id)
    assert rows[0].keys() == {"registration_id", "attendee_id", "attendee_name", "attendee_email", "event_id", "event_title", "event_starts_at", "status", "created_at"}
    assert AdminRegistrationService(repo, Notifications()).list_requests("approved", repo.event_id) == []


class NotificationRepo:
    def __init__(self): self.rows = []
    def list_owned(self, user_id): return sorted([row for row in self.rows if row["user_id"] == str(user_id)], key=lambda row: row["created_at"], reverse=True)
    def unread_count(self, user_id): return sum(row["user_id"] == str(user_id) and not row["is_read"] for row in self.rows)
    def mark_read(self, notification_id, user_id):
        for row in self.rows:
            if row["id"] == str(notification_id) and row["user_id"] == str(user_id): row["is_read"] = True; return row
        return None
    def mark_all_read(self, user_id):
        for row in self.rows:
            if row["user_id"] == str(user_id): row["is_read"] = True


def test_notification_read_operations_are_owner_scoped():
    owner, other = uuid4(), uuid4(); repo = NotificationRepo(); now = datetime.now(timezone.utc)
    first, second = uuid4(), uuid4()
    repo.rows = [{"id": str(first), "user_id": str(owner), "type": "registration_approved", "title": "A", "message": "A", "is_read": False, "event_id": None, "registration_id": None, "created_at": now}, {"id": str(second), "user_id": str(other), "type": "registration_rejected", "title": "B", "message": "B", "is_read": False, "event_id": None, "registration_id": None, "created_at": now}]
    service = NotificationService(repo)
    assert service.unread_count(owner).unread_count == 1
    assert service.mark_read(first, owner).is_read is True
    with pytest.raises(APIError): service.mark_read(second, owner)
    service.mark_all_read(owner)
    assert repo.rows[1]["is_read"] is False
