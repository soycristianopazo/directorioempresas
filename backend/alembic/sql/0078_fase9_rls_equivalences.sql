-- ============================================================================
-- 0078 · RLS de homologación cruzada + función compartida de autoría (fase 9.1/9.2)
-- ----------------------------------------------------------------------------
-- app.can_write_accreditation_program() centraliza la condición ya repetida
-- 3 veces en 0038_fase5_rls.sql (accreditation_programs_write,
-- requirement_groups_write, accreditation_requirements_write): PLATFORM →
-- platform.manage_taxonomy, ORGANIZATION → organization.update del dueño.
-- No reemplaza esas policies ya aplicadas (no hay necesidad — dan el mismo
-- resultado), pero SÍ la usan las policies nuevas de acá y el código Python
-- de fase 9 (_require_program_writer en services/accreditation.py).
-- ============================================================================

create or replace function app.can_write_accreditation_program(p_program_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.accreditation_programs ap
    where ap.id = p_program_id
      and (
        (ap.owner_scope = 'PLATFORM' and app.has_platform_permission('platform.manage_taxonomy'))
        or (ap.owner_scope = 'ORGANIZATION' and app.has_permission(ap.owner_organization_id, 'organization.update'))
      )
  );
$$;

grant execute on function app.can_write_accreditation_program(uuid) to app_user;

comment on function app.can_write_accreditation_program(uuid) is
  '¿Puede el usuario actual escribir sobre este programa (autoría, secciones, exigencias, equivalencias)? SECURITY DEFINER para poder reutilizarse en la policy de accreditation_program_equivalences sin repetir el EXISTS a mano.';


alter table public.accreditation_program_equivalences enable row level security;

create policy accreditation_program_equivalences_select
  on public.accreditation_program_equivalences for select
  using (true);

create policy accreditation_program_equivalences_write
  on public.accreditation_program_equivalences for all
  using (app.can_write_accreditation_program(program_id))
  with check (app.can_write_accreditation_program(program_id));

create policy accreditation_program_equivalences_system_context
  on public.accreditation_program_equivalences for all
  using (app.is_system_context()) with check (app.is_system_context());
