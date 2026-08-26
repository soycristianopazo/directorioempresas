-- ============================================================================
-- 0090 · Fixes de auditoría: RLS faltante + FK sin cascada
-- ----------------------------------------------------------------------------
-- Dos bugs reales encontrados en una auditoría de coherencia del proyecto.
-- ============================================================================

-- 1) sourcing_event_invitation_transitions (0044) nunca quedó con RLS
-- habilitado — a diferencia de su gemela accreditation_status_transitions
-- (0038), que sí sigue el patrón "catálogo de datos, lectura pública,
-- escritura de plataforma". Sin `enable row level security`, la tabla
-- queda legible/escribible por cualquiera con el rol app_user, sin policy
-- que lo filtre — 0010_hardening.sql otorga select/insert/update/delete en
-- todas las tablas por default. Mismo criterio que 0038, exactamente.
alter table public.sourcing_event_invitation_transitions enable row level security;

create policy sourcing_event_invitation_transitions_select
  on public.sourcing_event_invitation_transitions for select
  using (true);

create policy sourcing_event_invitation_transitions_write_platform
  on public.sourcing_event_invitation_transitions for all
  using (app.has_platform_permission('platform.manage_taxonomy'))
  with check (app.has_platform_permission('platform.manage_taxonomy'));

create policy sourcing_event_invitation_transitions_system_context
  on public.sourcing_event_invitation_transitions for all
  using (app.is_system_context()) with check (app.is_system_context());


-- 2) match_results.organization_id (0041) sin `on delete cascade` — mismo
-- bug ya encontrado y arreglado dos veces en este proyecto (0075, 0076):
-- borrar una organización con match_results asociados revienta con
-- "violates foreign key constraint match_results_organization_id_fkey" en
-- vez de arrastrar en cascada como el resto de sus FKs (match_run_id sí
-- tiene on delete cascade desde el origen).
alter table public.match_results
  drop constraint match_results_organization_id_fkey;

alter table public.match_results
  add constraint match_results_organization_id_fkey
  foreign key (organization_id) references public.organizations (id)
  on delete cascade;
