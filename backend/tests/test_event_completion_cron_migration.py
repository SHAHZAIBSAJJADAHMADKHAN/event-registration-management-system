from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "supabase"
    / "migrations"
    / "20260915000500_event_completion_cron.sql"
)


def test_event_completion_cron_uses_an_isolated_owner_only_core() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    assert "create extension if not exists pg_cron;" in sql
    assert "create schema if not exists event_lifecycle_private;" in sql
    assert "revoke all on schema event_lifecycle_private from public;" in sql
    assert "revoke all on schema event_lifecycle_private from anon, authenticated, service_role;" in sql
    assert "create or replace function event_lifecycle_private.complete_overdue_events_for_cron()" in sql
    assert "revoke all on function event_lifecycle_private.complete_overdue_events_for_cron() from public;" in sql
    assert "revoke execute on function event_lifecycle_private.complete_overdue_events_for_cron() from anon, authenticated, service_role;" in sql
    assert "create schema if not exists private;" not in sql


def test_event_completion_cron_preserves_public_service_role_guard_and_completion_scope() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    assert "create or replace function public.complete_overdue_events()" in sql
    assert "security definer" in sql
    assert "set search_path = public" in sql
    assert "if auth.role() <> 'service_role' then" in sql
    assert "return event_lifecycle_private.complete_overdue_events_for_cron();" in sql
    assert "status = 'published'" in sql
    assert "ends_at is not null" in sql
    assert "ends_at <= now()" in sql
    assert "set status = 'completed'" in sql
    assert "update public.registrations" not in sql
    assert "update public.notifications" not in sql
    assert "insert into public.notifications" not in sql
    assert "http" not in sql
    assert "apikey" not in sql


def test_event_completion_cron_has_one_stable_minute_job_without_direct_public_rpc_call() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    assert "select cron.schedule(" in sql
    assert "'event-completion-reconcile'" in sql
    assert "'* * * * *'" in sql
    assert "$cron$select event_lifecycle_private.complete_overdue_events_for_cron();$cron$" in sql
    assert "$cron$select public.complete_overdue_events();$cron$" not in sql
