from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "supabase"
    / "migrations"
    / "20260915000200_event_end_time_foundation.sql"
)


def test_end_time_migration_is_additive_and_preserves_legacy_rows() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    assert "add column ends_at timestamptz" in sql
    assert "events_ends_at_after_starts_at_check" in sql
    assert "ends_at is null or ends_at > starts_at" in sql
    assert "events_published_ends_at_idx" in sql
    assert "pg_cron" not in sql
    assert "not null" not in sql.split("add column ends_at timestamptz", 1)[1].split(";", 1)[0]
