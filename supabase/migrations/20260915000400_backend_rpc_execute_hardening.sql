-- Defense in depth for backend-only lifecycle and approval RPCs.

revoke execute on function public.complete_overdue_events() from public;
revoke execute on function public.complete_overdue_events() from anon, authenticated;
grant execute on function public.complete_overdue_events() to service_role;

revoke execute on function public.approve_registration_atomic(uuid) from public;
revoke execute on function public.approve_registration_atomic(uuid) from anon, authenticated;
grant execute on function public.approve_registration_atomic(uuid) to service_role;
