-- Phase 4: keep attendee cancellation within the event lifecycle boundary.

create or replace function public.cancel_registration_atomic(
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
  selected_event public.events;
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

  select * into selected_event
  from public.events
  where id = selected_registration.event_id
  for update;
  if not found then
    raise exception 'Event not found';
  end if;
  if selected_event.status in ('completed', 'cancelled') then
    raise exception 'Registration cancellation is closed for this event';
  end if;
  if selected_event.ends_at is not null and selected_event.ends_at <= now() then
    raise exception 'Registration cancellation is closed for this event';
  end if;

  update public.registrations
  set status = 'cancelled'
  where id = selected_registration.id
  returning * into selected_registration;
  return selected_registration;
end;
$$;

revoke execute on function public.cancel_registration_atomic(uuid, uuid) from public;
revoke execute on function public.cancel_registration_atomic(uuid, uuid) from anon, authenticated;
grant execute on function public.cancel_registration_atomic(uuid, uuid) to service_role;
