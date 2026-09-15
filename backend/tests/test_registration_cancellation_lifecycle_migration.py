from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "supabase"
    / "migrations"
    / "20260915000600_registration_cancellation_lifecycle_hardening.sql"
)


def test_cancellation_migration_locks_the_event_and_preserves_backend_only_access() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    assert "create or replace function public.cancel_registration_atomic(" in sql
    assert "security definer" in sql
    assert "set search_path = public" in sql
    assert "auth.role() <> 'service_role'" in sql
    assert "from public.events" in sql
    assert "where id = selected_registration.event_id" in sql
    assert "for update" in sql
    assert "selected_event.status in ('completed', 'cancelled')" in sql
    assert "selected_event.ends_at is not null and selected_event.ends_at <= now()" in sql
    assert "revoke execute on function public.cancel_registration_atomic(uuid, uuid) from public;" in sql
    assert "revoke execute on function public.cancel_registration_atomic(uuid, uuid) from anon, authenticated;" in sql
    assert "grant execute on function public.cancel_registration_atomic(uuid, uuid) to service_role;" in sql
    assert "update public.events" not in sql
    assert "update public.notifications" not in sql
