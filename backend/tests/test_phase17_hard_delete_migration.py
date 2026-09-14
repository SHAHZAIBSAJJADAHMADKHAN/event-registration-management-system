from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "supabase"
    / "migrations"
    / "20260915000100_admin_hard_delete_event.sql"
)


def test_hard_delete_rpc_is_atomic_and_service_role_only() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    assert "create or replace function public.delete_event_hard_atomic" in sql
    assert "if auth.role() <> 'service_role'" in sql
    assert "delete from public.notifications" in sql
    assert "registration_id in" in sql
    assert "delete from public.registrations where event_id = p_event_id" in sql
    assert "delete from public.events where id = p_event_id" in sql
    assert "revoke all on function public.delete_event_hard_atomic(uuid) from public" in sql
    assert "revoke all on function public.delete_event_hard_atomic(uuid) from anon, authenticated" in sql
    assert "grant execute on function public.delete_event_hard_atomic(uuid) to service_role" in sql
