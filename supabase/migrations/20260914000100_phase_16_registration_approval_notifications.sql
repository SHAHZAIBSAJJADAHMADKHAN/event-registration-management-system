-- Phase 16: approval-based registrations and persistent notification foundation.
-- This is a forward-only migration. It preserves existing registration rows.

drop function if exists public.create_registration_atomic(uuid, uuid);
drop index if exists public.registrations_one_active_per_attendee_event_idx;
drop index if exists public.registrations_event_active_idx;
drop trigger if exists events_prevent_capacity_below_active_registrations on public.events;
drop function if exists public.prevent_capacity_below_active_registrations();

-- PostgreSQL enum values cannot be safely removed in place. Replace the enum so
-- active disappears from the logical model while existing rows become approved.
alter table public.registrations alter column status drop default;
create type public.registration_status_phase16 as enum (
  'pending',
  'approved',
  'rejected',
  'cancelled'
);

alter table public.registrations
  alter column status type public.registration_status_phase16
  using (
    case status::text
      when 'active' then 'approved'
      else status::text
    end
  )::public.registration_status_phase16;

drop type public.registration_status;
alter type public.registration_status_phase16 rename to registration_status;
alter table public.registrations alter column status set default 'pending';

-- Only one open request may exist for an attendee/event. Rejected and cancelled
-- records remain as history and permit a later eligible request.
create unique index registrations_one_open_per_attendee_event_idx
  on public.registrations (attendee_id, event_id)
  where status in ('pending', 'approved');

create index registrations_event_approved_idx
  on public.registrations (event_id)
  where status = 'approved';

-- Capacity is consumed only by approved registrations.
create or replace function public.prevent_capacity_below_active_registrations()
returns trigger
language plpgsql
set search_path = public
as $$
declare
  approved_registration_count integer;
begin
  if new.capacity < old.capacity then
    select count(*) into approved_registration_count
    from public.registrations
    where event_id = old.id and status = 'approved';

    if new.capacity < approved_registration_count then
      raise exception 'Event capacity cannot be lower than approved registrations';
    end if;
  end if;

  return new;
end;
$$;

create trigger events_prevent_capacity_below_active_registrations
before update of capacity on public.events
for each row execute function public.prevent_capacity_below_active_registrations();

-- A request never reserves capacity. The current approved count is checked so a
-- full event does not accept additional requests.
create function public.create_registration_request_atomic(
  p_event_id uuid,
  p_attendee_id uuid
)
returns public.registrations
language plpgsql
security definer
set search_path = public
as $$
declare
  selected_event public.events;
  created_registration public.registrations;
  approved_registration_count integer;
begin
  if auth.role() <> 'service_role' then
    raise exception 'This operation is available only to the backend';
  end if;

  select * into selected_event
  from public.events
  where id = p_event_id
  for update;

  if not found then
    raise exception 'Event not found';
  end if;
  if selected_event.status <> 'published' then
    raise exception 'Registration is closed for this event';
  end if;
  if selected_event.starts_at <= now() then
    raise exception 'Registration is closed for past events';
  end if;
  if exists (
    select 1 from public.registrations
    where attendee_id = p_attendee_id
      and event_id = p_event_id
      and status in ('pending', 'approved')
  ) then
    raise exception 'An open registration request already exists for this event';
  end if;

  select count(*) into approved_registration_count
  from public.registrations
  where event_id = p_event_id and status = 'approved';
  if approved_registration_count >= selected_event.capacity then
    raise exception 'Event capacity has been reached';
  end if;

  insert into public.registrations (attendee_id, event_id, status)
  values (p_attendee_id, p_event_id, 'pending')
  returning * into created_registration;
  return created_registration;
end;
$$;

-- Approval serializes on both the pending registration and its event row. The
-- server must enforce the administrator role before invoking this RPC.
create function public.approve_registration_atomic(p_registration_id uuid)
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

create function public.reject_registration_atomic(p_registration_id uuid)
returns public.registrations
language plpgsql
security definer
set search_path = public
as $$
declare
  selected_registration public.registrations;
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

  update public.registrations
  set status = 'rejected'
  where id = selected_registration.id
  returning * into selected_registration;
  return selected_registration;
end;
$$;

-- Attendees may withdraw either a pending request or an approved registration.
create function public.cancel_registration_atomic(
  p_registration_id uuid,
  p_attendee_id uuid
)
returns public.registrations
language plpgsql
security definer
set search_path = public
as $$
declare
  selected_registration public.registrations;
begin
  if auth.role() <> 'service_role' then
    raise exception 'This operation is available only to the backend';
  end if;

  select * into selected_registration
  from public.registrations
  where id = p_registration_id
  for update;
  if not found or selected_registration.attendee_id <> p_attendee_id then
    raise exception 'Registration not found';
  end if;
  if selected_registration.status not in ('pending', 'approved') then
    raise exception 'Registration is not cancellable';
  end if;

  update public.registrations
  set status = 'cancelled'
  where id = selected_registration.id
  returning * into selected_registration;
  return selected_registration;
end;
$$;

create type public.notification_type as enum (
  'registration_request_submitted',
  'new_registration_request',
  'registration_approved',
  'registration_rejected',
  'registration_cancelled'
);

create table public.notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  type public.notification_type not null,
  title text not null check (char_length(btrim(title)) between 1 and 200),
  message text not null check (char_length(btrim(message)) between 1 and 2000),
  is_read boolean not null default false,
  event_id uuid references public.events(id) on delete set null,
  registration_id uuid references public.registrations(id) on delete set null,
  created_at timestamptz not null default now()
);

create index notifications_user_created_at_idx
  on public.notifications (user_id, created_at desc);

alter table public.notifications enable row level security;
create policy "notifications_select_own"
on public.notifications for select to authenticated
using (user_id = auth.uid());

revoke all on table public.notifications from anon, authenticated;
grant select on table public.notifications to authenticated;

revoke all on function public.create_registration_request_atomic(uuid, uuid) from public;
revoke all on function public.approve_registration_atomic(uuid) from public;
revoke all on function public.reject_registration_atomic(uuid) from public;
revoke all on function public.cancel_registration_atomic(uuid, uuid) from public;
grant execute on function public.create_registration_request_atomic(uuid, uuid) to service_role;
grant execute on function public.approve_registration_atomic(uuid) to service_role;
grant execute on function public.reject_registration_atomic(uuid) to service_role;
grant execute on function public.cancel_registration_atomic(uuid, uuid) to service_role;
