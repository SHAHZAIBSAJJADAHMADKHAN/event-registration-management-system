"""Opt-in Phase 16 live workflow verification using isolated, self-cleaning data."""
import os
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.core.config import Settings
from app.database.client import create_publishable_client, create_secret_client
from app.main import app

pytestmark = pytest.mark.skipif(os.getenv("RUN_SUPABASE_INTEGRATION_TESTS") != "true", reason="Set RUN_SUPABASE_INTEGRATION_TESTS=true for live verification.")

@pytest.fixture
def context():
    settings, secret = Settings(), create_secret_client(Settings())
    prefix, password, users, events = f"phase16-{uuid4().hex}", f"P16!{uuid4().hex}Aa", [], []
    def user(label):
        result = secret.auth.admin.create_user({"email": f"{prefix}-{label}@example.test", "password": password, "email_confirm": True, "user_metadata": {"full_name": f"Phase 16 {label}"}})
        users.append(result.user.id); return result.user.id
    try:
        admin_id, attendee_id = user("admin"), user("attendee")
        secret.rpc("provision_admin", {"p_profile_id": admin_id}).execute()
        event = secret.table("events").insert({"title": f"{prefix} event", "description": "Isolated Phase 16 verification", "starts_at": "2030-01-01T10:00:00Z", "location": "Integration test", "capacity": 1, "status": "published", "created_by": admin_id}).execute().data[0]
        events.append(event["id"])
        yield settings, secret, prefix, password, admin_id, attendee_id, event["id"]
    finally:
        for event_id in events: secret.table("registrations").delete().eq("event_id", event_id).execute(); secret.table("events").delete().eq("id", event_id).execute()
        for user_id in users: secret.auth.admin.delete_user(user_id)

def test_live_phase16_request_approval_cancellation_rejection_notifications(context):
    settings, _, prefix, password, _, _, event_id = context
    admin = create_publishable_client(settings).auth.sign_in_with_password({"email": f"{prefix}-admin@example.test", "password": password}).session
    attendee = create_publishable_client(settings).auth.sign_in_with_password({"email": f"{prefix}-attendee@example.test", "password": password}).session
    assert admin and attendee
    admin_headers, attendee_headers = {"Authorization": f"Bearer {admin.access_token}"}, {"Authorization": f"Bearer {attendee.access_token}"}
    with TestClient(app) as api:
        assert api.post(f"/api/events/{event_id}/registrations").status_code == 401
        request = api.post(f"/api/events/{event_id}/registrations", headers=attendee_headers); assert request.status_code == 201, request.json()
        registration = request.json(); assert registration["status"] == "pending"
        assert api.get(f"/api/events/{event_id}/my-registration", headers=attendee_headers).json()["status"] == "pending"
        event = api.get(f"/api/events/{event_id}", headers=attendee_headers).json(); assert event["active_registration_count"] == 0
        assert api.post(f"/api/events/{event_id}/registrations", headers=attendee_headers).status_code == 409
        assert api.get("/api/admin/registration-requests", headers=attendee_headers).status_code == 403
        requests = api.get("/api/admin/registration-requests", headers=admin_headers); assert requests.status_code == 200 and any(row["registration_id"] == registration["id"] for row in requests.json())
        approved = api.post(f"/api/admin/registration-requests/{registration['id']}/approve", headers=admin_headers); assert approved.status_code == 200, approved.json()
        assert approved.json()["status"] == "approved"
        assert api.get(f"/api/events/{event_id}", headers=attendee_headers).json()["active_registration_count"] == 1
        assert api.post(f"/api/admin/registration-requests/{registration['id']}/approve", headers=admin_headers).status_code == 409
        assert api.patch(f"/api/me/registrations/{registration['id']}/cancel", headers=attendee_headers).json()["status"] == "cancelled"
        assert api.get(f"/api/events/{event_id}", headers=attendee_headers).json()["active_registration_count"] == 0
        second = api.post(f"/api/events/{event_id}/registrations", headers=attendee_headers); assert second.status_code == 201
        assert api.post(f"/api/admin/registration-requests/{second.json()['id']}/reject", headers=admin_headers).json()["status"] == "rejected"
        notifications = api.get("/api/me/notifications", headers=attendee_headers); assert notifications.status_code == 200
        assert {"registration_request_submitted", "registration_approved", "registration_rejected"} <= {row["type"] for row in notifications.json()}
        unread = api.get("/api/me/notifications/unread-count", headers=attendee_headers); assert unread.json()["unread_count"] > 0
        assert api.patch(f"/api/me/notifications/{notifications.json()[0]['id']}/read", headers=attendee_headers).status_code == 200
        assert api.patch("/api/me/notifications/read-all", headers=attendee_headers).status_code == 204
        assert api.get("/api/me/notifications/unread-count", headers=attendee_headers).json()["unread_count"] == 0
        admin_notifications = api.get("/api/me/notifications", headers=admin_headers).json()
        assert any(row["type"] == "new_registration_request" for row in admin_notifications)
