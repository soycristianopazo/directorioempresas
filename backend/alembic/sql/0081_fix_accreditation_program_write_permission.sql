-- ============================================================================
-- 0081 · Fix: accreditation.manage no autorizaba escribir accreditation_programs (fase 9.2)
-- ----------------------------------------------------------------------------
-- Bug real encontrado en vivo (seed.py, no en el dry-run de migraciones):
-- "new row violates row-level security policy for table accreditation_programs"
-- al crear Roberto (BUYER_MANAGER, con accreditation.manage vía 0080) un
-- programa owner_scope=ORGANIZATION propio.
--
-- Causa: accreditation_programs_write (0038_fase5_rls.sql) y
-- app.can_write_accreditation_program() (0078, esta misma fase) gatean la
-- rama ORGANIZATION únicamente con organization.update — la única opción
-- que existía en fase 5, cuando "programa propio" era solo un campo del
-- modelo sin permiso dedicado. La capa Python (_require_program_writer en
-- services/accreditation.py) ya chequeaba accreditation.manage
-- correctamente desde el principio; RLS nunca se actualizó para aceptarlo
-- también — dos guardas independientes que dejaron de estar de acuerdo,
-- mismo tipo de bug que ya documenta docs/RLS.md sobre el patrón
-- backstop-permission.
--
-- Fix: ambas ramas (organization.update Y accreditation.manage) autorizan
-- la escritura — organization.update se mantiene porque ORG_OWNER (vía su
-- comodín '*') debe seguir pudiendo escribir sin depender de que alguien le
-- asigne accreditation.manage explícitamente.
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
        or (ap.owner_scope = 'ORGANIZATION' and (
          app.has_permission(ap.owner_organization_id, 'organization.update')
          or app.has_permission(ap.owner_organization_id, 'accreditation.manage')
        ))
      )
  );
$$;


drop policy accreditation_programs_write on public.accreditation_programs;

create policy accreditation_programs_write
  on public.accreditation_programs for all
  using (
    (owner_scope = 'PLATFORM' and app.has_platform_permission('platform.manage_taxonomy'))
    or (owner_scope = 'ORGANIZATION' and (
      app.has_permission(owner_organization_id, 'organization.update')
      or app.has_permission(owner_organization_id, 'accreditation.manage')
    ))
  )
  with check (
    (owner_scope = 'PLATFORM' and app.has_platform_permission('platform.manage_taxonomy'))
    or (owner_scope = 'ORGANIZATION' and (
      app.has_permission(owner_organization_id, 'organization.update')
      or app.has_permission(owner_organization_id, 'accreditation.manage')
    ))
  );


do $$
declare
  t text;
  tables text[] := array['requirement_groups', 'accreditation_requirements'];
begin
  foreach t in array tables loop
    execute format('drop policy %I on public.%I', t || '_write', t);
    execute format(
      'create policy %I on public.%I for all using ('
      '  exists (select 1 from public.accreditation_programs ap '
      '          where ap.id = program_id and ('
      '            (ap.owner_scope = ''PLATFORM'' and app.has_platform_permission(''platform.manage_taxonomy''))'
      '            or (ap.owner_scope = ''ORGANIZATION'' and ('
      '              app.has_permission(ap.owner_organization_id, ''organization.update'')'
      '              or app.has_permission(ap.owner_organization_id, ''accreditation.manage'')'
      '            ))'
      '          ))'
      ') with check ('
      '  exists (select 1 from public.accreditation_programs ap '
      '          where ap.id = program_id and ('
      '            (ap.owner_scope = ''PLATFORM'' and app.has_platform_permission(''platform.manage_taxonomy''))'
      '            or (ap.owner_scope = ''ORGANIZATION'' and ('
      '              app.has_permission(ap.owner_organization_id, ''organization.update'')'
      '              or app.has_permission(ap.owner_organization_id, ''accreditation.manage'')'
      '            ))'
      '          ))'
      ')', t || '_write', t
    );
  end loop;
end $$;
