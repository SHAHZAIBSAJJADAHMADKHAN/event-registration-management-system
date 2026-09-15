-- Phase 3: database-native scheduling for authoritative event completion.
-- pg_cron jobs execute as their scheduling database role and do not carry
-- Supabase request JWT claims, so they use the owner-only core below.

create extension if not exists pg_cron;

create schema if not exists event_lifecycle_private;
revoke all on schema event_lifecycle_private from public;
revoke all on schema event_lifecycle_private from anon, authenticated, service_role;

create or replace function event_lifecycle_private.complete_overdue_events_for_cron()
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  completed_count integer;
begin
  with completed_events as (
    update public.events
    set status = 'completed'
    where status = 'published'
      and ends_at is not null
      and ends_at <= now()
    returning id
  )
  select count(*) into completed_count from completed_events;

  return completed_count;
end;
$$;

revoke all on function event_lifecycle_private.complete_overdue_events_for_cron() from public;
revoke execute on function event_lifecycle_private.complete_overdue_events_for_cron() from anon, authenticated, service_role;

-- Preserve the existing backend-only public contract and delegate its one
-- authoritative completion operation to the same private core used by Cron.
create or replace function public.complete_overdue_events()
returns integer
language plpgsql
security definer
set search_path = public
as $$
begin
  if auth.role() <> 'service_role' then
    raise exception 'This operation is available only to the backend';
  end if;

  return event_lifecycle_private.complete_overdue_events_for_cron();
end;
$$;

-- A named pg_cron job is replaced when the same name is scheduled again.
select cron.schedule(
  'event-completion-reconcile',
  '* * * * *',
  $cron$select event_lifecycle_private.complete_overdue_events_for_cron();$cron$
);
