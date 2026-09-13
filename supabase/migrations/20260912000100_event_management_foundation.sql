-- Phase 1: Event Registration & Management System foundation.
-- Apply with the Supabase CLI or migration runner. This migration is idempotent
-- only through migration tracking; do not run it manually against a database
-- where the same objects already exist.

create extension if not exists pgcrypto;

create type public.user_role as enum ('admin', 'attendee');
create type public.event_status as enum ('draft', 'published', 'completed', 'cancelled');
create type public.registration_status as enum ('active', 'cancelled');

create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text not null check (char_length(btrim(full_name)) between 1 and 200),
  role public.user_role not null default 'attendee',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.events (
  id uuid primary key default gen_random_uuid(),
  title text not null check (char_length(btrim(title)) between 1 and 200),
  description text not null check (char_length(btrim(description)) between 1 and 10000),
  starts_at timestamptz not null,
  location text not null check (char_length(btrim(location)) between 1 and 300),
  capacity integer not null check (capacity > 0),
  status public.event_status not null default 'draft',
  created_by uuid not null references public.profiles(id) on delete restrict,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.registrations (
  id uuid primary key default gen_random_uuid(),
  attendee_id uuid not null references public.profiles(id) on delete restrict,
  event_id uuid not null references public.events(id) on delete restrict,
  status public.registration_status not null default 'active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Prevent concurrent or repeated active registrations while retaining cancellation history.
create unique index registrations_one_active_per_attendee_event_idx
  on public.registrations (attendee_id, event_id)
  where status = 'active';

create index events_discovery_idx
  on public.events (starts_at)
  where status = 'published';

create index registrations_event_active_idx
  on public.registrations (event_id)
  where status = 'active';

create index registrations_attendee_idx on public.registrations (attendee_id);

create function public.set_updated_at()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger profiles_set_updated_at
before update on public.profiles
for each row execute function public.set_updated_at();

create trigger events_set_updated_at
before update on public.events
for each row execute function public.set_updated_at();

create trigger registrations_set_updated_at
before update on public.registrations
for each row execute function public.set_updated_at();

-- Auth sign-up metadata may provide a display name, but never a role.
create function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, full_name, role)
  values (
    new.id,
    coalesce(nullif(btrim(new.raw_user_meta_data ->> 'full_name'), ''), 'New attendee'),
    'attendee'
  );
  return new;
end;
$$;

create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.handle_new_user();

-- Prevent self-escalation through direct PostgREST profile updates.
create function public.protect_profile_identity_and_role()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  if new.id <> old.id then
    raise exception 'Profile identity cannot be changed';
  end if;

  if new.created_at <> old.created_at then
    raise exception 'Profile creation timestamp cannot be changed';
  end if;

  if new.role <> old.role and auth.role() <> 'service_role' then
    raise exception 'Only a server-side administrative process may change roles';
  end if;

  return new;
end;
$$;

create trigger profiles_protect_identity_and_role
before update on public.profiles
for each row execute function public.protect_profile_identity_and_role();

-- Only an existing administrator can be recorded as an event creator.
create function public.require_admin_event_creator()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  if not exists (
    select 1 from public.profiles
    where id = new.created_by and role = 'admin'
  ) then
    raise exception 'Event creator must have the admin role';
  end if;
  return new;
end;
$$;

create trigger events_require_admin_creator
before insert or update of created_by on public.events
for each row execute function public.require_admin_event_creator();

-- Capacity cannot be lowered below the current number of active registrations.
create function public.prevent_capacity_below_active_registrations()
returns trigger
language plpgsql
set search_path = public
as $$
declare
  active_registration_count integer;
begin
  if new.capacity < old.capacity then
    select count(*) into active_registration_count
    from public.registrations
    where event_id = old.id and status = 'active';

    if new.capacity < active_registration_count then
      raise exception 'Event capacity cannot be lower than active registrations';
    end if;
  end if;

  return new;
end;
$$;

create trigger events_prevent_capacity_below_active_registrations
before update of capacity on public.events
for each row execute function public.prevent_capacity_below_active_registrations();

-- Future FastAPI registration services call this function with the JWT-verified
-- attendee id using server credentials. It serializes attempts for one event.
create function public.create_registration_atomic(
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
  active_registration_count integer;
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
      and status = 'active'
  ) then
    raise exception 'An active registration already exists for this event';
  end if;

  select count(*) into active_registration_count
  from public.registrations
  where event_id = p_event_id and status = 'active';

  if active_registration_count >= selected_event.capacity then
    raise exception 'Event capacity has been reached';
  end if;

  insert into public.registrations (attendee_id, event_id, status)
  values (p_attendee_id, p_event_id, 'active')
  returning * into created_registration;

  return created_registration;
end;
$$;

-- A controlled role-provisioning entry point for a trusted server process.
create function public.provision_admin(p_profile_id uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  if auth.role() <> 'service_role' then
    raise exception 'Admin provisioning is available only to the backend';
  end if;

  update public.profiles
  set role = 'admin'
  where id = p_profile_id;

  if not found then
    raise exception 'Profile not found';
  end if;
end;
$$;

alter table public.profiles enable row level security;
alter table public.events enable row level security;
alter table public.registrations enable row level security;

-- Profiles: authenticated people may read and edit their own profile only.
create policy "profiles_select_own"
on public.profiles for select to authenticated
using (id = auth.uid());

create policy "profiles_update_own"
on public.profiles for update to authenticated
using (id = auth.uid())
with check (id = auth.uid());

-- Events: public discovery can read published event information. Writes stay
-- backend-only; the service role bypasses RLS after FastAPI authorizes the call.
create policy "events_select_published"
on public.events for select to anon, authenticated
using (status = 'published');

-- Registrations: people may read only their own records. No direct public writes
-- are permitted; FastAPI will use the server-only atomic RPC in a later phase.
create policy "registrations_select_own"
on public.registrations for select to authenticated
using (attendee_id = auth.uid());

revoke all on function public.create_registration_atomic(uuid, uuid) from public;
revoke all on function public.provision_admin(uuid) from public;
grant execute on function public.create_registration_atomic(uuid, uuid) to service_role;
grant execute on function public.provision_admin(uuid) to service_role;
