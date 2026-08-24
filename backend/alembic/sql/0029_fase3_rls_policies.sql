-- ============================================================================
-- 0029 · RLS de perfil extendido y catálogo de oferta
-- ----------------------------------------------------------------------------
-- Fase 3.6 del roadmap. Sin FORCE ROW LEVEL SECURITY — mismo motivo de
-- siempre, ver 0010_hardening.sql.
-- ============================================================================

do $$
declare
  t text;
  -- Tablas org-escopadas sin columna is_public propia: la visibilidad la
  -- decide enteramente la organización dueña (app.can_view_organization).
  org_scoped_tables text[] := array[
    'organization_locations', 'organization_media',
    'organization_industries', 'organization_territories',
    'organization_certifications'
  ];
begin
  foreach t in array org_scoped_tables loop
    execute format('alter table public.%I enable row level security', t);

    execute format(
      'create policy %I on public.%I for select using (app.can_view_organization(organization_id))',
      t || '_select', t
    );
    execute format(
      'create policy %I on public.%I for all '
      'using (app.has_permission(organization_id, ''organization.update'')) '
      'with check (app.has_permission(organization_id, ''organization.update''))',
      t || '_write', t
    );
    execute format(
      'create policy %I on public.%I for all '
      'using (app.is_system_context()) with check (app.is_system_context())',
      t || '_system_context', t
    );
  end loop;
end $$;


-- ============================================================================
-- organization_contacts — is_public propia además de la visibilidad de la org
-- ============================================================================

alter table public.organization_contacts enable row level security;

create policy organization_contacts_select
  on public.organization_contacts for select
  using (
    (is_public and app.can_view_organization(organization_id))
    or app.has_permission(organization_id, 'organization.update')
    or app.is_member_of(organization_id)
    or app.is_platform_admin()
  );

create policy organization_contacts_write
  on public.organization_contacts for all
  using (app.has_permission(organization_id, 'organization.update'))
  with check (app.has_permission(organization_id, 'organization.update'));

create policy organization_contacts_system_context
  on public.organization_contacts for all
  using (app.is_system_context()) with check (app.is_system_context());


-- ============================================================================
-- organization_settings — nunca público, ni siquiera para todo el equipo
-- ============================================================================

alter table public.organization_settings enable row level security;

create policy organization_settings_select
  on public.organization_settings for select
  using (app.is_member_of(organization_id) or app.is_platform_admin());

create policy organization_settings_write
  on public.organization_settings for all
  using (app.has_permission(organization_id, 'organization.update'))
  with check (app.has_permission(organization_id, 'organization.update'));

create policy organization_settings_system_context
  on public.organization_settings for all
  using (app.is_system_context()) with check (app.is_system_context());


-- ============================================================================
-- client_references, case_studies — is_public propia
-- ============================================================================

do $$
declare
  t text;
  tables text[] := array['client_references', 'case_studies'];
begin
  foreach t in array tables loop
    execute format('alter table public.%I enable row level security', t);

    execute format(
      'create policy %I on public.%I for select using ('
      '  (is_public and app.can_view_organization(organization_id))'
      '  or app.has_permission(organization_id, ''organization.update'')'
      '  or app.is_member_of(organization_id)'
      '  or app.is_platform_admin()'
      ')', t || '_select', t
    );
    execute format(
      'create policy %I on public.%I for all '
      'using (app.has_permission(organization_id, ''organization.update'')) '
      'with check (app.has_permission(organization_id, ''organization.update''))',
      t || '_write', t
    );
    execute format(
      'create policy %I on public.%I for all '
      'using (app.is_system_context()) with check (app.is_system_context())',
      t || '_system_context', t
    );
  end loop;
end $$;


-- ============================================================================
-- case_study_taxonomy_nodes, case_study_media — heredan de case_studies
-- ============================================================================

alter table public.case_study_taxonomy_nodes enable row level security;

create policy case_study_taxonomy_nodes_select
  on public.case_study_taxonomy_nodes for select
  using (
    exists (
      select 1 from public.case_studies cs
      where cs.id = case_study_id
        and (
          (cs.is_public and app.can_view_organization(cs.organization_id))
          or app.has_permission(cs.organization_id, 'organization.update')
          or app.is_member_of(cs.organization_id)
          or app.is_platform_admin()
        )
    )
  );

create policy case_study_taxonomy_nodes_write
  on public.case_study_taxonomy_nodes for all
  using (
    exists (
      select 1 from public.case_studies cs
      where cs.id = case_study_id and app.has_permission(cs.organization_id, 'organization.update')
    )
  )
  with check (
    exists (
      select 1 from public.case_studies cs
      where cs.id = case_study_id and app.has_permission(cs.organization_id, 'organization.update')
    )
  );

create policy case_study_taxonomy_nodes_system_context
  on public.case_study_taxonomy_nodes for all
  using (app.is_system_context()) with check (app.is_system_context());


alter table public.case_study_media enable row level security;

create policy case_study_media_select
  on public.case_study_media for select
  using (
    exists (
      select 1 from public.case_studies cs
      where cs.id = case_study_id
        and (
          (cs.is_public and app.can_view_organization(cs.organization_id))
          or app.has_permission(cs.organization_id, 'organization.update')
          or app.is_member_of(cs.organization_id)
          or app.is_platform_admin()
        )
    )
  );

create policy case_study_media_write
  on public.case_study_media for all
  using (
    exists (
      select 1 from public.case_studies cs
      where cs.id = case_study_id and app.has_permission(cs.organization_id, 'organization.update')
    )
  )
  with check (
    exists (
      select 1 from public.case_studies cs
      where cs.id = case_study_id and app.has_permission(cs.organization_id, 'organization.update')
    )
  );

create policy case_study_media_system_context
  on public.case_study_media for all
  using (app.is_system_context()) with check (app.is_system_context());


-- ============================================================================
-- certification_types — catálogo de plataforma, mismo criterio que taxonomía
-- ============================================================================

alter table public.certification_types enable row level security;

create policy certification_types_select_public
  on public.certification_types for select
  using (true);

create policy certification_types_write_platform
  on public.certification_types for all
  using (app.has_platform_permission('platform.manage_taxonomy'))
  with check (app.has_platform_permission('platform.manage_taxonomy'));

create policy certification_types_system_context
  on public.certification_types for all
  using (app.is_system_context()) with check (app.is_system_context());


-- ============================================================================
-- supplier_offerings
-- ============================================================================

alter table public.supplier_offerings enable row level security;

create policy supplier_offerings_select
  on public.supplier_offerings for select
  using (app.can_view_offering(id));

-- Sin policy de INSERT separada: for all cubre create/update, y el DELETE
-- real no existe (deleted_at es una columna UPDATE, mismo patrón que
-- organizations). offering.write cubre altas y ediciones de borrador;
-- offering.publish y offering.delete se verifican ADEMÁS a nivel de
-- servicio antes de la transición específica (publicar / archivar) — ver
-- services/offerings.py. RLS es el backstop grueso, no el único lugar
-- donde se decide qué acción específica puede hacer cada rol.
create policy supplier_offerings_write
  on public.supplier_offerings for all
  using (
    app.has_permission(organization_id, 'offering.write')
    or app.has_permission(organization_id, 'offering.publish')
    or app.has_permission(organization_id, 'offering.delete')
  )
  with check (
    app.has_permission(organization_id, 'offering.write')
    or app.has_permission(organization_id, 'offering.publish')
    or app.has_permission(organization_id, 'offering.delete')
  );

create policy supplier_offerings_system_context
  on public.supplier_offerings for all
  using (app.is_system_context()) with check (app.is_system_context());


-- ============================================================================
-- Tablas hijas de supplier_offerings — visibilidad y escritura heredadas
-- ============================================================================

do $$
declare
  t text;
  tables text[] := array[
    'offering_taxonomy_nodes', 'offering_industries', 'offering_territories',
    'offering_media', 'offering_attribute_values', 'offering_attribute_option_values'
  ];
begin
  foreach t in array tables loop
    execute format('alter table public.%I enable row level security', t);

    -- offering_attribute_option_values no tiene offering_id directo: cuelga
    -- de offering_attribute_values. El resto sí lo tiene.
    if t = 'offering_attribute_option_values' then
      execute format(
        'create policy %I on public.%I for select using ('
        '  exists (select 1 from public.offering_attribute_values v '
        '          where v.id = offering_attribute_value_id and app.can_view_offering(v.offering_id))'
        ')', t || '_select', t
      );
      execute format(
        'create policy %I on public.%I for all using ('
        '  exists (select 1 from public.offering_attribute_values v '
        '          join public.supplier_offerings so on so.id = v.offering_id '
        '          where v.id = offering_attribute_value_id and app.has_permission(so.organization_id, ''offering.write''))'
        ') with check ('
        '  exists (select 1 from public.offering_attribute_values v '
        '          join public.supplier_offerings so on so.id = v.offering_id '
        '          where v.id = offering_attribute_value_id and app.has_permission(so.organization_id, ''offering.write''))'
        ')', t || '_write', t
      );
    else
      execute format(
        'create policy %I on public.%I for select using (app.can_view_offering(offering_id))',
        t || '_select', t
      );
      execute format(
        'create policy %I on public.%I for all using ('
        '  exists (select 1 from public.supplier_offerings so '
        '          where so.id = offering_id and app.has_permission(so.organization_id, ''offering.write''))'
        ') with check ('
        '  exists (select 1 from public.supplier_offerings so '
        '          where so.id = offering_id and app.has_permission(so.organization_id, ''offering.write''))'
        ')', t || '_write', t
      );
    end if;

    execute format(
      'create policy %I on public.%I for all '
      'using (app.is_system_context()) with check (app.is_system_context())',
      t || '_system_context', t
    );
  end loop;
end $$;


-- ============================================================================
-- offering_pricing, offering_documents — is_public propia además de la
-- visibilidad del offering
-- ============================================================================

do $$
declare
  t text;
  tables text[] := array['offering_pricing', 'offering_documents'];
begin
  foreach t in array tables loop
    execute format('alter table public.%I enable row level security', t);

    execute format(
      'create policy %I on public.%I for select using ('
      '  (is_public and app.can_view_offering(offering_id))'
      '  or exists (select 1 from public.supplier_offerings so '
      '             where so.id = offering_id and app.has_permission(so.organization_id, ''offering.read''))'
      '  or app.is_platform_admin()'
      ')', t || '_select', t
    );
    execute format(
      'create policy %I on public.%I for all using ('
      '  exists (select 1 from public.supplier_offerings so '
      '          where so.id = offering_id and app.has_permission(so.organization_id, ''offering.write''))'
      ') with check ('
      '  exists (select 1 from public.supplier_offerings so '
      '          where so.id = offering_id and app.has_permission(so.organization_id, ''offering.write''))'
      ')', t || '_write', t
    );
    execute format(
      'create policy %I on public.%I for all '
      'using (app.is_system_context()) with check (app.is_system_context())',
      t || '_system_context', t
    );
  end loop;
end $$;
