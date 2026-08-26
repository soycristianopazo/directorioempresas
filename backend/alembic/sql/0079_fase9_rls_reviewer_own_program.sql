-- ============================================================================
-- 0079 · RLS del revisor de programa propio (fase 9.3)
-- ----------------------------------------------------------------------------
-- Hasta acá, revisar una postulación era exclusivo de
-- platform.review_accreditation (el revisor de plataforma). Fase 9 agrega un
-- segundo revisor posible: el comprador dueño de un programa
-- owner_scope=ORGANIZATION, vía accreditation.manage sobre SU organización.
-- Extiende (drop+create, nunca edita) las policies ya aplicadas por
-- 0038_fase5_rls.sql — mismo patrón que 0074 (is_negotiation_round_participant)
-- y 0052 (is_conversation_participant): una función SECURITY DEFINER STABLE
-- para no repetir el EXISTS a mano y para poder anidarla en las tablas que
-- cuelgan de accreditation_enrollments vía join.
--
-- organization_documents/organization_document_versions ganan la misma rama
-- SOLO en SELECT (el revisor de programa propio ve evidencia, nunca la
-- sube/edita — igual que ya vale para el revisor de plataforma) y acotada al
-- documento específico enviado como evidencia de un fulfillment de SU
-- programa — a propósito más estricta que el precedente de
-- platform.review_accreditation, que da acceso de lectura a TODOS los
-- documentos de TODAS las organizaciones sin acotar a fulfillments reales:
-- un comprador es una contraparte de negocio, no un empleado neutral de
-- plataforma, así que no hereda ese mismo alcance amplio.
-- ============================================================================

create or replace function app.is_own_program_reviewer(p_program_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.accreditation_programs ap
    where ap.id = p_program_id
      and ap.owner_scope = 'ORGANIZATION'
      and app.has_permission(ap.owner_organization_id, 'accreditation.manage')
  );
$$;

grant execute on function app.is_own_program_reviewer(uuid) to app_user;

comment on function app.is_own_program_reviewer(uuid) is
  '¿Tiene el usuario actual accreditation.manage sobre la organización dueña de este programa (owner_scope=ORGANIZATION)? Revisor de programa propio, fase 9 — distinto de platform.review_accreditation (revisor de plataforma, programas PLATFORM).';


create or replace function app.is_own_program_reviewer_for_document_version(p_document_version_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.accreditation_fulfillments af
    join public.accreditation_enrollments ae on ae.id = af.enrollment_id
    where af.document_version_id = p_document_version_id
      and app.is_own_program_reviewer(ae.program_id)
  );
$$;

grant execute on function app.is_own_program_reviewer_for_document_version(uuid) to app_user;

comment on function app.is_own_program_reviewer_for_document_version(uuid) is
  '¿Fue esta versión de documento enviada como evidencia de un fulfillment de un programa propio que el usuario actual revisa? Acota la lectura del revisor de programa propio a evidencia real, a diferencia del alcance amplio de platform.review_accreditation.';


create or replace function app.is_own_program_reviewer_for_document(p_document_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.organization_document_versions v
    join public.accreditation_fulfillments af on af.document_version_id = v.id
    join public.accreditation_enrollments ae on ae.id = af.enrollment_id
    where v.document_id = p_document_id
      and app.is_own_program_reviewer(ae.program_id)
  );
$$;

grant execute on function app.is_own_program_reviewer_for_document(uuid) to app_user;

comment on function app.is_own_program_reviewer_for_document(uuid) is
  'Mismo criterio que is_own_program_reviewer_for_document_version(), a nivel del documento (organization_documents) en vez de una versión puntual.';


-- ── accreditation_enrollments ──────────────────────────────────────────────

drop policy accreditation_enrollments_select on public.accreditation_enrollments;

create policy accreditation_enrollments_select
  on public.accreditation_enrollments for select
  using (
    app.has_permission(organization_id, 'accreditation.submit')
    or app.has_permission(organization_id, 'accreditation.manage')
    or app.has_platform_permission('platform.review_accreditation')
    or app.is_platform_admin()
    or app.is_own_program_reviewer(program_id)
  );

drop policy accreditation_enrollments_write on public.accreditation_enrollments;

create policy accreditation_enrollments_write
  on public.accreditation_enrollments for all
  using (
    app.has_permission(organization_id, 'accreditation.submit')
    or app.has_permission(organization_id, 'accreditation.manage')
    or app.has_platform_permission('platform.review_accreditation')
    or app.is_own_program_reviewer(program_id)
  )
  with check (
    app.has_permission(organization_id, 'accreditation.submit')
    or app.has_permission(organization_id, 'accreditation.manage')
    or app.has_platform_permission('platform.review_accreditation')
    or app.is_own_program_reviewer(program_id)
  );


-- ── Tablas que cuelgan de accreditation_enrollments ────────────────────────

do $$
declare
  t text;
  tables text[] := array[
    'accreditation_fulfillments', 'accreditation_section_progress',
    'accreditation_status_history'
  ];
begin
  foreach t in array tables loop
    execute format('drop policy %I on public.%I', t || '_select', t);
    execute format(
      'create policy %I on public.%I for select using ('
      '  exists (select 1 from public.accreditation_enrollments ae '
      '          where ae.id = enrollment_id and ('
      '            app.has_permission(ae.organization_id, ''accreditation.submit'')'
      '            or app.has_permission(ae.organization_id, ''accreditation.manage'')'
      '            or app.has_platform_permission(''platform.review_accreditation'')'
      '            or app.is_platform_admin()'
      '            or app.is_own_program_reviewer(ae.program_id)'
      '          ))'
      ')', t || '_select', t
    );

    execute format('drop policy %I on public.%I', t || '_write', t);
    execute format(
      'create policy %I on public.%I for all using ('
      '  exists (select 1 from public.accreditation_enrollments ae '
      '          where ae.id = enrollment_id and ('
      '            app.has_permission(ae.organization_id, ''accreditation.submit'')'
      '            or app.has_permission(ae.organization_id, ''accreditation.manage'')'
      '            or app.has_platform_permission(''platform.review_accreditation'')'
      '            or app.is_own_program_reviewer(ae.program_id)'
      '          ))'
      ') with check ('
      '  exists (select 1 from public.accreditation_enrollments ae '
      '          where ae.id = enrollment_id and ('
      '            app.has_permission(ae.organization_id, ''accreditation.submit'')'
      '            or app.has_permission(ae.organization_id, ''accreditation.manage'')'
      '            or app.has_platform_permission(''platform.review_accreditation'')'
      '            or app.is_own_program_reviewer(ae.program_id)'
      '          ))'
      ')', t || '_write', t
    );
  end loop;
end $$;


-- ── accreditation_review_events (cuelga de accreditation_fulfillments) ────

drop policy accreditation_review_events_select on public.accreditation_review_events;

create policy accreditation_review_events_select
  on public.accreditation_review_events for select
  using (
    exists (
      select 1 from public.accreditation_fulfillments af
      join public.accreditation_enrollments ae on ae.id = af.enrollment_id
      where af.id = fulfillment_id and (
        app.has_permission(ae.organization_id, 'accreditation.submit')
        or app.has_permission(ae.organization_id, 'accreditation.manage')
        or app.has_platform_permission('platform.review_accreditation')
        or app.is_platform_admin()
        or app.is_own_program_reviewer(ae.program_id)
      )
    )
  );

drop policy accreditation_review_events_write on public.accreditation_review_events;

create policy accreditation_review_events_write
  on public.accreditation_review_events for all
  using (
    exists (
      select 1 from public.accreditation_fulfillments af
      join public.accreditation_enrollments ae on ae.id = af.enrollment_id
      where af.id = fulfillment_id and (
        app.has_permission(ae.organization_id, 'accreditation.submit')
        or app.has_permission(ae.organization_id, 'accreditation.manage')
        or app.has_platform_permission('platform.review_accreditation')
        or app.is_own_program_reviewer(ae.program_id)
      )
    )
  )
  with check (
    exists (
      select 1 from public.accreditation_fulfillments af
      join public.accreditation_enrollments ae on ae.id = af.enrollment_id
      where af.id = fulfillment_id and (
        app.has_permission(ae.organization_id, 'accreditation.submit')
        or app.has_permission(ae.organization_id, 'accreditation.manage')
        or app.has_platform_permission('platform.review_accreditation')
        or app.is_own_program_reviewer(ae.program_id)
      )
    )
  );


-- ── organization_documents / organization_document_versions — solo SELECT ──

drop policy organization_documents_select on public.organization_documents;

create policy organization_documents_select
  on public.organization_documents for select
  using (
    app.has_permission(organization_id, 'document.read')
    or app.has_platform_permission('platform.review_accreditation')
    or app.is_platform_admin()
    or app.is_own_program_reviewer_for_document(id)
  );

drop policy organization_document_versions_select on public.organization_document_versions;

create policy organization_document_versions_select
  on public.organization_document_versions for select
  using (
    exists (
      select 1 from public.organization_documents od
      where od.id = document_id
        and (
          app.has_permission(od.organization_id, 'document.read')
          or app.has_platform_permission('platform.review_accreditation')
          or app.is_platform_admin()
        )
    )
    or app.is_own_program_reviewer_for_document_version(id)
  );
