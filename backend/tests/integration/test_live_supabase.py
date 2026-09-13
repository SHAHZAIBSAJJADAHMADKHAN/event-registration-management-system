"""Opt-in live Supabase verification; never runs in the normal unit suite."""

import os
from uuid import uuid4

import pytest
from postgrest.exceptions import APIError
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.database.client import create_publishable_client, create_secret_client
from app.main import app

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_SUPABASE_INTEGRATION_TESTS") != "true",
    reason="Set RUN_SUPABASE_INTEGRATION_TESTS=true to run against the development project.",
)


def expect_api_error(operation, code: str) -> APIError:
    with pytest.raises(APIError) as raised:
        operation()
    assert raised.value.code == code
    return raised.value


@pytest.fixture
def live_context():
    """Create isolated development data and always remove it after verification."""
    settings = Settings()
    secret = create_secret_client(settings)
    prefix = f"phase2-{uuid4().hex}"
    password = f"P2!{uuid4().hex}Aa"
    users: list[str] = []
    event_ids: list[str] = []

    def create_user(label: str) -> str:
        result = secret.auth.admin.create_user(
            {
                "email": f"{prefix}-{label}@example.test",
                "password": password,
                "email_confirm": True,
                "user_metadata": {"full_name": f"Phase 2 {label}"},
            }
        )
        assert result.user is not None
        user_id = result.user.id
        users.append(user_id)
        return user_id

    try:
        admin_id = create_user("admin")
        attendee_a_id = create_user("attendee-a")
        attendee_b_id = create_user("attendee-b")

        secret.rpc("provision_admin", {"p_profile_id": admin_id}).execute()
        profiles = (
            secret.table("profiles")
            .select("id,role,created_at,updated_at")
            .in_("id", [admin_id, attendee_a_id, attendee_b_id])
            .execute()
            .data
        )
        roles = {profile["id"]: profile["role"] for profile in profiles}
        assert roles[admin_id] == "admin"
        assert roles[attendee_a_id] == "attendee"
        assert roles[attendee_b_id] == "attendee"
        assert all(profile["created_at"] and profile["updated_at"] for profile in profiles)

        def create_event(
            capacity: int,
            status: str = "published",
            starts_at: str = "2030-01-01T10:00:00Z",
        ) -> str:
            result = (
                secret.table("events")
                .insert(
                    {
                        "title": f"{prefix} event",
                        "description": "Phase 2 integration verification event",
                        "starts_at": starts_at,
                        "location": "Integration test location",
                        "capacity": capacity,
                        "status": status,
                        "created_by": admin_id,
                    }
                )
                .execute()
            )
            event_id = result.data[0]["id"]
            event_ids.append(event_id)
            return event_id

        yield {
            "settings": settings,
            "secret": secret,
            "prefix": prefix,
            "password": password,
            "admin_id": admin_id,
            "attendee_a_id": attendee_a_id,
            "attendee_b_id": attendee_b_id,
            "create_event": create_event,
            "event_ids": event_ids,
        }
    finally:
        for event_id in event_ids:
            secret.table("registrations").delete().eq("event_id", event_id).execute()
        for event_id in event_ids:
            secret.table("events").delete().eq("id", event_id).execute()
        for user_id in users:
            secret.auth.admin.delete_user(user_id)


def test_live_phase_two_database_foundation(live_context) -> None:
    secret = live_context["secret"]
    create_event = live_context["create_event"]
    admin_id = live_context["admin_id"]
    attendee_a_id = live_context["attendee_a_id"]
    attendee_b_id = live_context["attendee_b_id"]

    # Invalid writes must fail and do not persist.
    expect_api_error(
        lambda: secret.table("events").insert(
            {
                "title": "invalid capacity",
                "description": "invalid capacity",
                "starts_at": "2030-01-01T10:00:00Z",
                "location": "Integration test location",
                "capacity": 0,
                "status": "draft",
                "created_by": admin_id,
            }
        ).execute(),
        "23514",
    )
    expect_api_error(
        lambda: secret.table("events").insert(
            {
                "title": "invalid status",
                "description": "invalid status",
                "starts_at": "2030-01-01T10:00:00Z",
                "location": "Integration test location",
                "capacity": 1,
                "status": "invalid",
                "created_by": admin_id,
            }
        ).execute(),
        "22P02",
    )
    expect_api_error(
        lambda: secret.table("registrations").insert(
            {
                "attendee_id": attendee_a_id,
                "event_id": str(uuid4()),
                "status": "invalid",
            }
        ).execute(),
        "22P02",
    )
    expect_api_error(
        lambda: secret.table("registrations").insert(
            {
                "attendee_id": str(uuid4()),
                "event_id": str(uuid4()),
                "status": "active",
            }
        ).execute(),
        "23503",
    )

    event_id = create_event(capacity=1)
    event = secret.table("events").select("created_at,updated_at").eq("id", event_id).execute().data[0]
    assert event["created_at"] and event["updated_at"]
    first_registration = secret.rpc(
        "create_registration_atomic",
        {"p_event_id": event_id, "p_attendee_id": attendee_a_id},
    ).execute().data
    assert first_registration["status"] == "active"

    duplicate_error = expect_api_error(
        lambda: secret.rpc(
            "create_registration_atomic",
            {"p_event_id": event_id, "p_attendee_id": attendee_a_id},
        ).execute(),
        "P0001",
    )
    assert "already exists" in duplicate_error.message.lower()

    capacity_error = expect_api_error(
        lambda: secret.rpc(
            "create_registration_atomic",
            {"p_event_id": event_id, "p_attendee_id": attendee_b_id},
        ).execute(),
        "P0001",
    )
    assert "capacity" in capacity_error.message.lower()

    secret.table("registrations").update({"status": "cancelled"}).eq(
        "id", first_registration["id"]
    ).execute()
    replacement = secret.table("registrations").insert(
        {"attendee_id": attendee_a_id, "event_id": event_id, "status": "active"}
    ).execute().data[0]
    assert replacement["status"] == "active"
    expect_api_error(
        lambda: secret.table("registrations").insert(
            {"attendee_id": attendee_a_id, "event_id": event_id, "status": "active"}
        ).execute(),
        "23505",
    )
    capacity_reduction_error = expect_api_error(
        lambda: secret.table("events").update({"capacity": 0}).eq("id", event_id).execute(),
        "P0001",
    )
    assert "lower than active registrations" in capacity_reduction_error.message.lower()

    # Authenticate two isolated attendees with publishable-key clients to prove RLS.
    attendee_a_client = create_publishable_client(live_context["settings"])
    attendee_b_client = create_publishable_client(live_context["settings"])
    attendee_a_auth = attendee_a_client.auth.sign_in_with_password(
        {
            "email": f"{live_context['prefix']}-attendee-a@example.test",
            "password": live_context["password"],
        }
    )
    attendee_b_client.auth.sign_in_with_password(
        {
            "email": f"{live_context['prefix']}-attendee-b@example.test",
            "password": live_context["password"],
        }
    )

    own_rows = attendee_a_client.table("registrations").select("id").eq(
        "id", replacement["id"]
    ).execute().data
    other_rows = attendee_b_client.table("registrations").select("id").eq(
        "id", replacement["id"]
    ).execute().data
    assert len(own_rows) == 1
    assert other_rows == []

    own_profile = attendee_a_client.table("profiles").select("id").eq(
        "id", attendee_a_id
    ).execute().data
    other_profile = attendee_b_client.table("profiles").select("id").eq(
        "id", attendee_a_id
    ).execute().data
    assert len(own_profile) == 1
    assert other_profile == []

    promotion_error = expect_api_error(
        lambda: attendee_a_client.table("profiles").update({"role": "admin"}).eq(
            "id", attendee_a_id
        ).execute(),
        "P0001",
    )
    assert "administrative process" in promotion_error.message.lower()

    assert attendee_a_auth.session is not None
    with TestClient(app) as api:
        current_user_response = api.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {attendee_a_auth.session.access_token}"},
        )
    assert current_user_response.status_code == 200
    assert current_user_response.json()["id"] == attendee_a_id
    assert current_user_response.json()["role"] == "attendee"

    anonymous_client = create_publishable_client(live_context["settings"])
    assert anonymous_client.table("registrations").select("id").limit(1).execute().data == []
    published_event_rows = anonymous_client.table("events").select("id").eq(
        "id", event_id
    ).execute().data
    assert len(published_event_rows) == 1


def test_live_phase_four_admin_event_management(live_context) -> None:
    settings = live_context["settings"]
    prefix = live_context["prefix"]
    password = live_context["password"]
    admin_id = live_context["admin_id"]
    event_ids = live_context["event_ids"]

    admin_client = create_publishable_client(settings)
    attendee_client = create_publishable_client(settings)
    admin_auth = admin_client.auth.sign_in_with_password(
        {"email": f"{prefix}-admin@example.test", "password": password}
    )
    attendee_auth = attendee_client.auth.sign_in_with_password(
        {"email": f"{prefix}-attendee-a@example.test", "password": password}
    )
    assert admin_auth.session is not None
    assert attendee_auth.session is not None

    headers = {"Authorization": f"Bearer {admin_auth.session.access_token}"}
    attendee_headers = {"Authorization": f"Bearer {attendee_auth.session.access_token}"}
    payload = {
        "title": f"{prefix} admin event",
        "description": "Phase 4 live verification event",
        "starts_at": "2030-01-01T10:00:00Z",
        "location": "Integration test location",
        "capacity": 2,
        "status": "draft",
    }

    with TestClient(app) as api:
        attendee_response = api.post("/api/admin/events", json=payload, headers=attendee_headers)
        assert attendee_response.status_code == 403, attendee_response.json()

        created = api.post("/api/admin/events", json=payload, headers=headers)
        assert created.status_code == 201
        event = created.json()
        event_ids.append(event["id"])
        assert event["created_by"] == admin_id
        assert event["status"] == "draft"

        listed = api.get("/api/admin/events", headers=headers)
        assert listed.status_code == 200
        assert any(row["id"] == event["id"] for row in listed.json())
        assert api.get(f"/api/admin/events/{event['id']}", headers=headers).status_code == 200

        updated = api.patch(
            f"/api/admin/events/{event['id']}",
            json={"title": f"{prefix} updated admin event"},
            headers=headers,
        )
        assert updated.status_code == 200
        assert updated.json()["title"] == f"{prefix} updated admin event"
        assert api.patch(
            f"/api/admin/events/{event['id']}/status",
            json={"status": "completed"},
            headers=headers,
        ).status_code == 409
        assert api.patch(
            f"/api/admin/events/{event['id']}/status",
            json={"status": "published"},
            headers=headers,
        ).status_code == 200
        assert api.patch(
            f"/api/admin/events/{event['id']}/status",
            json={"status": "completed"},
            headers=headers,
        ).status_code == 200


def test_live_phase_five_event_discovery(live_context) -> None:
    settings = live_context["settings"]
    secret = live_context["secret"]
    create_event = live_context["create_event"]
    prefix = live_context["prefix"]
    password = live_context["password"]
    attendee_a_id = live_context["attendee_a_id"]
    attendee_b_id = live_context["attendee_b_id"]

    published_future_id = create_event(capacity=3, status="published")
    draft_id = create_event(capacity=3, status="draft")
    cancelled_id = create_event(capacity=3, status="cancelled")
    completed_id = create_event(capacity=3, status="completed")
    past_id = create_event(
        capacity=3, status="published", starts_at="2020-01-01T10:00:00Z"
    )
    secret.rpc(
        "create_registration_atomic",
        {"p_event_id": published_future_id, "p_attendee_id": attendee_a_id},
    ).execute()
    cancelled_registration = secret.table("registrations").insert(
        {
            "attendee_id": attendee_b_id,
            "event_id": published_future_id,
            "status": "active",
        }
    ).execute().data[0]
    secret.table("registrations").update({"status": "cancelled"}).eq(
        "id", cancelled_registration["id"]
    ).execute()

    attendee_auth = create_publishable_client(settings).auth.sign_in_with_password(
        {"email": f"{prefix}-attendee-a@example.test", "password": password}
    )
    assert attendee_auth.session is not None
    headers = {"Authorization": f"Bearer {attendee_auth.session.access_token}"}

    with TestClient(app) as api:
        assert api.get("/api/events").status_code == 401
        listing = api.get("/api/events", headers=headers)
        assert listing.status_code == 200
        rows = {row["id"]: row for row in listing.json()}
        assert published_future_id in rows
        assert draft_id not in rows
        assert cancelled_id not in rows
        assert completed_id not in rows
        assert past_id not in rows
        assert rows[published_future_id]["active_registration_count"] == 1
        assert rows[published_future_id]["remaining_availability"] == 2

        assert api.get(f"/api/events/{published_future_id}", headers=headers).status_code == 200
        assert api.get(f"/api/events/{draft_id}", headers=headers).status_code == 404


def test_live_phase_six_registration_lifecycle(live_context) -> None:
    settings = live_context["settings"]
    create_event = live_context["create_event"]
    prefix = live_context["prefix"]
    password = live_context["password"]

    published_id = create_event(capacity=1, status="published")
    draft_id = create_event(capacity=1, status="draft")
    cancelled_id = create_event(capacity=1, status="cancelled")
    completed_id = create_event(capacity=1, status="completed")
    past_id = create_event(
        capacity=1, status="published", starts_at="2020-01-01T10:00:00Z"
    )
    attendee_a_auth = create_publishable_client(settings).auth.sign_in_with_password(
        {"email": f"{prefix}-attendee-a@example.test", "password": password}
    )
    attendee_b_auth = create_publishable_client(settings).auth.sign_in_with_password(
        {"email": f"{prefix}-attendee-b@example.test", "password": password}
    )
    assert attendee_a_auth.session is not None
    assert attendee_b_auth.session is not None
    attendee_a_headers = {"Authorization": f"Bearer {attendee_a_auth.session.access_token}"}
    attendee_b_headers = {"Authorization": f"Bearer {attendee_b_auth.session.access_token}"}

    with TestClient(app) as api:
        assert api.post(f"/api/events/{published_id}/registrations").status_code == 401
        created = api.post(
            f"/api/events/{published_id}/registrations", headers=attendee_a_headers
        )
        assert created.status_code == 201
        registration = created.json()
        assert registration["status"] == "active"
        assert api.post(
            f"/api/events/{published_id}/registrations", headers=attendee_a_headers
        ).status_code == 409
        assert api.post(
            f"/api/events/{published_id}/registrations", headers=attendee_b_headers
        ).status_code == 409

        mine = api.get("/api/me/registrations", headers=attendee_a_headers)
        assert mine.status_code == 200
        assert any(row["id"] == registration["id"] for row in mine.json())
        assert api.get(
            f"/api/me/registrations/{registration['id']}", headers=attendee_b_headers
        ).status_code == 404
        assert api.patch(
            f"/api/me/registrations/{registration['id']}/cancel", headers=attendee_b_headers
        ).status_code == 404

        cancelled = api.patch(
            f"/api/me/registrations/{registration['id']}/cancel", headers=attendee_a_headers
        )
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"
        assert api.patch(
            f"/api/me/registrations/{registration['id']}/cancel", headers=attendee_a_headers
        ).status_code == 409

        listing = api.get("/api/events", headers=attendee_a_headers)
        row = next(item for item in listing.json() if item["id"] == published_id)
        assert row["active_registration_count"] == 0
        assert row["remaining_availability"] == 1
        assert api.post(
            f"/api/events/{published_id}/registrations", headers=attendee_a_headers
        ).status_code == 201

        for event_id in (draft_id, cancelled_id, completed_id, past_id):
            assert api.post(
                f"/api/events/{event_id}/registrations", headers=attendee_a_headers
            ).status_code == 409


def test_live_phase_seven_admin_operations(live_context) -> None:
    settings = live_context["settings"]
    secret = live_context["secret"]
    create_event = live_context["create_event"]
    prefix = live_context["prefix"]
    password = live_context["password"]
    attendee_a_id = live_context["attendee_a_id"]
    attendee_b_id = live_context["attendee_b_id"]

    event_id = create_event(capacity=3, status="published")
    secret.rpc(
        "create_registration_atomic",
        {"p_event_id": event_id, "p_attendee_id": attendee_a_id},
    ).execute()
    cancelled = secret.table("registrations").insert(
        {"attendee_id": attendee_b_id, "event_id": event_id, "status": "active"}
    ).execute().data[0]
    secret.table("registrations").update({"status": "cancelled"}).eq(
        "id", cancelled["id"]
    ).execute()

    admin_auth = create_publishable_client(settings).auth.sign_in_with_password(
        {"email": f"{prefix}-admin@example.test", "password": password}
    )
    attendee_auth = create_publishable_client(settings).auth.sign_in_with_password(
        {"email": f"{prefix}-attendee-a@example.test", "password": password}
    )
    assert admin_auth.session is not None
    assert attendee_auth.session is not None
    admin_headers = {"Authorization": f"Bearer {admin_auth.session.access_token}"}
    attendee_headers = {"Authorization": f"Bearer {attendee_auth.session.access_token}"}

    with TestClient(app) as api:
        assert api.get("/api/admin/dashboard").status_code == 401
        assert api.get("/api/admin/dashboard", headers=attendee_headers).status_code == 403

        attendees = api.get(f"/api/admin/events/{event_id}/attendees", headers=admin_headers)
        assert attendees.status_code == 200, attendees.json()
        assert {row["registration_status"] for row in attendees.json()} == {"active", "cancelled"}
        assert all(row["attendee_email"].endswith("@example.test") for row in attendees.json())

        active = api.get(
            f"/api/admin/events/{event_id}/attendees?status=active", headers=admin_headers
        )
        assert active.status_code == 200
        assert len(active.json()) == 1
        summary = api.get(f"/api/admin/events/{event_id}/summary", headers=admin_headers)
        assert summary.status_code == 200
        assert summary.json()["active_registrations"] == 1
        assert summary.json()["cancelled_registrations"] == 1
        assert summary.json()["remaining_availability"] == 2

        check_in = api.get(f"/api/admin/events/{event_id}/check-in", headers=admin_headers)
        assert check_in.status_code == 200
        assert len(check_in.json()) == 1
        export = api.get(f"/api/admin/events/{event_id}/attendees/export.csv", headers=admin_headers)
        assert export.status_code == 200
        assert export.headers["content-type"].startswith("text/csv")
        assert "Registration ID" in export.text
