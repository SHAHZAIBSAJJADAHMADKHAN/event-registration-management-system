-- Phase 17.1: controlled, backend-only hard deletion of an event and its data.
-- PostgreSQL functions execute atomically: an error rolls back notification,
-- registration, and event deletion together.
create or replace function public.delete_event_hard_atomic(p_event_id uuid)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
begin
  if auth.role() <> 'service_role' then
    raise exception 'This operation is available only to the backend';
  end if;

  if not exists (select 1 from public.events where id = p_event_id) then
    raise exception 'Event not found';
  end if;

  delete from public.notifications
  where event_id = p_event_id
     or registration_id in (
       select id from public.registrations where event_id = p_event_id
     );

  delete from public.registrations where event_id = p_event_id;
  delete from public.events where id = p_event_id;
  return true;
end;
$$;

revoke all on function public.delete_event_hard_atomic(uuid) from public;
revoke all on function public.delete_event_hard_atomic(uuid) from anon, authenticated;
grant execute on function public.delete_event_hard_atomic(uuid) to service_role;
