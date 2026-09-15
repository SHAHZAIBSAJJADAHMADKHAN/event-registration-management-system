-- Phase 2: database-owned, idempotent completion of ended published events.
-- This migration deliberately does not configure a scheduler.

create or replace function public.complete_overdue_events()
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  completed_count integer;
begin
  if auth.role() <> 'service_role' then
    raise exception 'This operation is available only to the backend';
  end if;

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

-- Approval already locks both the pending registration and its event row.
-- Keep that atomic behavior while refusing approvals after a known end time.
create or replace function public.approve_registration_atomic(p_registration_id uuid)
returns public.registrations
language plpgsql
security definer
set search_path = public
as $$
declare
  selected_registration public.registrations;
  selected_event public.events;
  approved_registration_count integer;
begin
  if auth.role() <> 'service_role' then
    raise exception 'This operation is available only to the backend';
  end if;

  select * into selected_registration
  from public.registrations
  where id = p_registration_id
  for update;
  if not found then
    raise exception 'Registration not found';
  end if;
  if selected_registration.status <> 'pending' then
    raise exception 'Registration request is no longer pending';
  end if;

  select * into selected_event
  from public.events
  where id = selected_registration.event_id
  for update;
  if not found then
    raise exception 'Event not found';
  end if;
  if selected_event.status <> 'published' then
    raise exception 'Registration is closed for this event';
  end if;
  if selected_event.ends_at is not null and selected_event.ends_at <= now() then
    raise exception 'Registration is closed for this event';
  end if;
  if selected_event.starts_at <= now() then
    raise exception 'Registration is closed for past events';
  end if;

  select count(*) into approved_registration_count
  from public.registrations
  where event_id = selected_event.id and status = 'approved';
  if approved_registration_count >= selected_event.capacity then
    raise exception 'Event capacity has been reached';
  end if;

  update public.registrations
  set status = 'approved'
  where id = selected_registration.id
  returning * into selected_registration;
  return selected_registration;
end;
$$;
