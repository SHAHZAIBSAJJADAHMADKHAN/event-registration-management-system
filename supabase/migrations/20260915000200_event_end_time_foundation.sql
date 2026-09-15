-- Phase 1: additive event end-time foundation.
-- Existing events retain NULL ends_at until an administrator supplies a verified value.

alter table public.events
  add column ends_at timestamptz;

alter table public.events
  add constraint events_ends_at_after_starts_at_check
  check (ends_at is null or ends_at > starts_at);

-- Supports a future authoritative completion query without affecting legacy rows.
create index events_published_ends_at_idx
  on public.events (ends_at)
  where status = 'published' and ends_at is not null;
