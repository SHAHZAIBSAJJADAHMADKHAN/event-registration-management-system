from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "supabase"
    / "migrations"
    / "20260914000100_phase_16_registration_approval_notifications.sql"
)


def migration_sql() -> str:
    return MIGRATION.read_text(encoding="utf-8").lower()


def test_active_rows_upgrade_to_approved_without_recreating_registrations() -> None:
    sql = migration_sql()

    assert "when 'active' then 'approved'" in sql
    assert "alter column status type public.registration_status_phase16" in sql
    assert "drop table public.registrations" not in sql


def test_open_request_uniqueness_and_approved_only_capacity_are_enforced() -> None:
    sql = migration_sql()

    assert "registrations_one_open_per_attendee_event_idx" in sql
    assert "where status in ('pending', 'approved')" in sql
    assert "registrations_event_approved_idx" in sql
    assert "where event_id = old.id and status = 'approved'" in sql


def test_atomic_request_approval_rejection_and_cancellation_rpcs_exist() -> None:
    sql = migration_sql()

    for function in (
        "create_registration_request_atomic",
        "approve_registration_atomic",
        "reject_registration_atomic",
        "cancel_registration_atomic",
    ):
        assert f"create function public.{function}" in sql
    assert "for update" in sql
    assert "set status = 'pending'" not in sql
    assert "values (p_attendee_id, p_event_id, 'pending')" in sql
    assert "set status = 'approved'" in sql
    assert "set status = 'rejected'" in sql
    assert "set status = 'cancelled'" in sql
    assert "approved_registration_count >= selected_event.capacity" in sql


def test_notification_storage_is_owned_and_server_write_only() -> None:
    sql = migration_sql()

    assert "create table public.notifications" in sql
    assert "create type public.notification_type" in sql
    assert "notifications_select_own" in sql
    assert "using (user_id = auth.uid())" in sql
    assert "revoke all on table public.notifications from anon, authenticated" in sql
    assert "grant select on table public.notifications to authenticated" in sql
    assert "grant execute on function public.approve_registration_atomic(uuid) to service_role" in sql
