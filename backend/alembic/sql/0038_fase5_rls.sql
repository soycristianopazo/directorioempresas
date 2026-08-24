-- ============================================================================
-- 0038 · RLS de acreditación, documentos y badges
-- ----------------------------------------------------------------------------
-- Fase 5 del roadmap. Sin FORCE ROW LEVEL SECURITY — mismo motivo de
-- siempre, ver 0010_hardening.sql.
-- ============================================================================

-- ============================================================================
-- document_types — catálogo de plataforma, mismo criterio que certification_types
-- ============================================================================

alter table public.document_types enable row level security;

create policy document_types_select_public
  on public.document_types for select
  using (true);

create policy document_types_write_platform
  on public.document_types for all
  using (app.has_platform_permission('platform.manage_taxonomy'))
  with check (app.has_platform_permission('platform.manage_taxonomy'));

create policy document_types_system_context
  on public.document_types for all
  using (app.is_system_context()) with check (app.is_system_context());


-- ============================================================================
-- organization_documents / organization_document_versions — NUNCA público,
-- ni siquiera vía can_view_organization: es evidencia privada. La ve la
-- propia organización o un revisor de plataforma.
-- ============================================================================

alter table public.organization_documents enable row level security;

create policy organization_documents_select
  on public.organization_documents for select
  using (
    app.has_permission(organization_id, 'document.read')
    or app.has_platform_permission('platform.review_accreditation')
    or app.is_platform_admin()
  );

create policy organization_documents_write
  on public.organization_documents for all
  using (
    app.has_permission(organization_id, 'document.write')
    or app.has_permission(organization_id, 'document.delete')
  )
  with check (
    app.has_permission(organization_id, 'document.write')
    or app.has_permission(organization_id, 'document.delete')
  );

create policy organization_documents_system_context
  on public.organization_documents for all
  using (app.is_system_context()) with check (app.is_system_context());


alter table public.organization_document_versions enable row level security;

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
  );

create policy organization_document_versions_write
  on public.organization_document_versions for all
  using (
    exists (
      select 1 from public.organization_documents od
      where od.id = document_id
        and (
          app.has_permission(od.organization_id, 'document.write')
          or app.has_permission(od.organization_id, 'document.delete')
        )
    )
  )
  with check (
    exists (
      select 1 from public.organization_documents od
      where od.id = document_id
        and (
          app.has_permission(od.organization_id, 'document.write')
          or app.has_permission(od.organization_id, 'document.delete')
        )
    )
  );

create policy organization_document_versions_system_context
  on public.organization_document_versions for all
  using (app.is_system_context()) with check (app.is_system_context());


-- ============================================================================
-- accreditation_programs, requirement_groups, accreditation_requirements —
-- lectura pública (hay que poder ver las exigencias antes de postular),
-- escritura de programas PLATFORM por platform.manage_taxonomy, programas
-- ORGANIZATION por su propio organization.update (autoría de programa
-- propio — el modelo lo soporta aunque esta fase no construye su UI).
-- accreditation_status_transitions es catálogo de referencia, mismo criterio
-- que document_types.
-- ============================================================================

alter table public.accreditation_programs enable row level security;

create policy accreditation_programs_select
  on public.accreditation_programs for select
  using (is_active or app.is_platform_admin());

create policy accreditation_programs_write
  on public.accreditation_programs for all
  using (
    (owner_scope = 'PLATFORM' and app.has_platform_permission('platform.manage_taxonomy'))
    or (owner_scope = 'ORGANIZATION' and app.has_permission(owner_organization_id, 'organization.update'))
  )
  with check (
    (owner_scope = 'PLATFORM' and app.has_platform_permission('platform.manage_taxonomy'))
    or (owner_scope = 'ORGANIZATION' and app.has_permission(owner_organization_id, 'organization.update'))
  );

create policy accreditation_programs_system_context
  on public.accreditation_programs for all
  using (app.is_system_context()) with check (app.is_system_context());


do $$
declare
  t text;
  tables text[] := array['requirement_groups', 'accreditation_requirements'];
begin
  foreach t in array tables loop
    execute format('alter table public.%I enable row level security', t);

    execute format(
      'create policy %I on public.%I for select using (true)',
      t || '_select', t
    );
    execute format(
      'create policy %I on public.%I for all using ('
      '  exists (select 1 from public.accreditation_programs ap '
      '          where ap.id = program_id and ('
      '            (ap.owner_scope = ''PLATFORM'' and app.has_platform_permission(''platform.manage_taxonomy''))'
      '            or (ap.owner_scope = ''ORGANIZATION'' and app.has_permission(ap.owner_organization_id, ''organization.update''))'
      '          ))'
      ') with check ('
      '  exists (select 1 from public.accreditation_programs ap '
      '          where ap.id = program_id and ('
      '            (ap.owner_scope = ''PLATFORM'' and app.has_platform_permission(''platform.manage_taxonomy''))'
      '            or (ap.owner_scope = ''ORGANIZATION'' and app.has_permission(ap.owner_organization_id, ''organization.update''))'
      '          ))'
      ')', t || '_write', t
    );
    execute format(
      'create policy %I on public.%I for all '
      'using (app.is_system_context()) with check (app.is_system_context())',
      t || '_system_context', t
    );
  end loop;
end $$;


alter table public.accreditation_status_transitions enable row level security;

create policy accreditation_status_transitions_select
  on public.accreditation_status_transitions for select
  using (true);

create policy accreditation_status_transitions_write_platform
  on public.accreditation_status_transitions for all
  using (app.has_platform_permission('platform.manage_taxonomy'))
  with check (app.has_platform_permission('platform.manage_taxonomy'));

create policy accreditation_status_transitions_system_context
  on public.accreditation_status_transitions for all
  using (app.is_system_context()) with check (app.is_system_context());


-- ============================================================================
-- accreditation_enrollments y todo lo que cuelga de un enrollment —
-- backstop grueso: la organización postulante (accreditation.submit/manage)
-- O el revisor de plataforma (platform.review_accreditation) tocan las
-- mismas filas por razones distintas. La distinción fina ("el proveedor
-- nunca decide su propio estado") vive en services/accreditation.py, no
-- acá — mismo patrón que supplier_offerings (fase 3).
-- ============================================================================

alter table public.accreditation_enrollments enable row level security;

create policy accreditation_enrollments_select
  on public.accreditation_enrollments for select
  using (
    app.has_permission(organization_id, 'accreditation.submit')
    or app.has_permission(organization_id, 'accreditation.manage')
    or app.has_platform_permission('platform.review_accreditation')
    or app.is_platform_admin()
  );

create policy accreditation_enrollments_write
  on public.accreditation_enrollments for all
  using (
    app.has_permission(organization_id, 'accreditation.submit')
    or app.has_permission(organization_id, 'accreditation.manage')
    or app.has_platform_permission('platform.review_accreditation')
  )
  with check (
    app.has_permission(organization_id, 'accreditation.submit')
    or app.has_permission(organization_id, 'accreditation.manage')
    or app.has_platform_permission('platform.review_accreditation')
  );

create policy accreditation_enrollments_system_context
  on public.accreditation_enrollments for all
  using (app.is_system_context()) with check (app.is_system_context());


do $$
declare
  t text;
  tables text[] := array[
    'accreditation_fulfillments', 'accreditation_section_progress',
    'accreditation_status_history'
  ];
begin
  foreach t in array tables loop
    execute format('alter table public.%I enable row level security', t);

    execute format(
      'create policy %I on public.%I for select using ('
      '  exists (select 1 from public.accreditation_enrollments ae '
      '          where ae.id = enrollment_id and ('
      '            app.has_permission(ae.organization_id, ''accreditation.submit'')'
      '            or app.has_permission(ae.organization_id, ''accreditation.manage'')'
      '            or app.has_platform_permission(''platform.review_accreditation'')'
      '            or app.is_platform_admin()'
      '          ))'
      ')', t || '_select', t
    );
    execute format(
      'create policy %I on public.%I for all using ('
      '  exists (select 1 from public.accreditation_enrollments ae '
      '          where ae.id = enrollment_id and ('
      '            app.has_permission(ae.organization_id, ''accreditation.submit'')'
      '            or app.has_permission(ae.organization_id, ''accreditation.manage'')'
      '            or app.has_platform_permission(''platform.review_accreditation'')'
      '          ))'
      ') with check ('
      '  exists (select 1 from public.accreditation_enrollments ae '
      '          where ae.id = enrollment_id and ('
      '            app.has_permission(ae.organization_id, ''accreditation.submit'')'
      '            or app.has_permission(ae.organization_id, ''accreditation.manage'')'
      '            or app.has_platform_permission(''platform.review_accreditation'')'
      '          ))'
      ')', t || '_write', t
    );
    execute format(
      'create policy %I on public.%I for all '
      'using (app.is_system_context()) with check (app.is_system_context())',
      t || '_system_context', t
    );
  end loop;
end $$;


-- accreditation_review_events cuelga de accreditation_fulfillments, no
-- directamente de accreditation_enrollments — un salto más en el JOIN.
alter table public.accreditation_review_events enable row level security;

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
      )
    )
  );

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
      )
    )
  );

create policy accreditation_review_events_system_context
  on public.accreditation_review_events for all
  using (app.is_system_context()) with check (app.is_system_context());


-- ============================================================================
-- badge_definitions — catálogo, mismo criterio que document_types.
-- organization_badges — lectura PÚBLICA (es la señal de confianza que se
-- muestra en el perfil público, fase 4); escritura solo revisor/sistema,
-- nunca la organización misma.
-- ============================================================================

alter table public.badge_definitions enable row level security;

create policy badge_definitions_select_public
  on public.badge_definitions for select
  using (true);

create policy badge_definitions_write_platform
  on public.badge_definitions for all
  using (app.has_platform_permission('platform.manage_taxonomy'))
  with check (app.has_platform_permission('platform.manage_taxonomy'));

create policy badge_definitions_system_context
  on public.badge_definitions for all
  using (app.is_system_context()) with check (app.is_system_context());


alter table public.organization_badges enable row level security;

create policy organization_badges_select
  on public.organization_badges for select
  using (
    (revoked_at is null and app.can_view_organization(organization_id))
    or app.is_member_of(organization_id)
    or app.is_platform_admin()
  );

create policy organization_badges_write
  on public.organization_badges for all
  using (app.has_platform_permission('platform.review_accreditation') or app.is_platform_admin())
  with check (app.has_platform_permission('platform.review_accreditation') or app.is_platform_admin());

create policy organization_badges_system_context
  on public.organization_badges for all
  using (app.is_system_context()) with check (app.is_system_context());
