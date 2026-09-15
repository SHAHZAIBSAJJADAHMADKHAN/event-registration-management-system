from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "supabase"
    / "migrations"
    / "20260915000400_backend_rpc_execute_hardening.sql"
)


def test_backend_rpc_execute_hardening_is_forward_only_and_scoped() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    for signature in (
        "public.complete_overdue_events()",
        "public.approve_registration_atomic(uuid)",
    ):
        assert f"revoke execute on function {signature} from public;" in sql
        assert f"revoke execute on function {signature} from anon, authenticated;" in sql
        assert f"grant execute on function {signature} to service_role;" in sql

    assert "create function" not in sql
    assert "create or replace function" not in sql
    assert "update public.events" not in sql
    assert "update public.registrations" not in sql
    assert "pg_cron" not in sql
    assert "cron.schedule" not in sql
