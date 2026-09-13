from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "supabase"
    / "migrations"
    / "20260912000100_event_management_foundation.sql"
)


def migration_sql() -> str:
    return MIGRATION.read_text(encoding="utf-8").lower()


def test_migration_defines_required_tables_and_relationships() -> None:
    sql = migration_sql()

    assert "create table public.profiles" in sql
    assert "references auth.users(id) on delete cascade" in sql
    assert "create table public.events" in sql
    assert "created_by uuid not null references public.profiles(id)" in sql
    assert "create table public.registrations" in sql
    assert "attendee_id uuid not null references public.profiles(id)" in sql
    assert "event_id uuid not null references public.events(id)" in sql


def test_migration_enforces_status_and_capacity_integrity() -> None:
    sql = migration_sql()

    assert "create type public.event_status as enum ('draft', 'published', 'completed', 'cancelled')" in sql
    assert "create type public.registration_status as enum ('active', 'cancelled')" in sql
    assert "capacity integer not null check (capacity > 0)" in sql
    assert "events_prevent_capacity_below_active_registrations" in sql


def test_migration_preserves_cancelled_history_but_blocks_duplicate_active_rows() -> None:
    sql = migration_sql()

    assert "create unique index registrations_one_active_per_attendee_event_idx" in sql
    assert "where status = 'active'" in sql
    assert "status public.registration_status not null default 'active'" in sql


def test_migration_includes_atomic_registration_and_rls_foundation() -> None:
    sql = migration_sql()

    assert "create function public.create_registration_atomic" in sql
    assert "for update" in sql
    assert "active_registration_count >= selected_event.capacity" in sql
    assert "alter table public.profiles enable row level security" in sql
    assert "profiles_select_own" in sql
    assert "registrations_select_own" in sql
    assert "only a server-side administrative process may change roles" in sql
