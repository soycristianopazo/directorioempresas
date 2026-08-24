-- ============================================================================
-- 0049 · RLS de cotizaciones — modo sellado (fase 7.6)
-- ----------------------------------------------------------------------------
-- La policy más revisada del sistema. Punto de control 7 del roadmap: "test
-- que demuestra que el Proveedor B no puede leer ninguna fila de la oferta
-- del Proveedor A, ni por API ni por Realtime, en ningún estado del evento."
--
-- Patrón E (docs/01-ARQUITECTURA.md §I.3), no el backstop de permisos de
-- 0043/0048: quotations lleva supplier_organization_id PROPIO por fila, y la
-- policy compara app.is_member_of(supplier_organization_id) directamente
-- contra la columna de esa fila — no una organización fija de la tabla. El
-- proveedor B nunca puede volverse "verdadero" contra la fila del proveedor
-- A porque is_member_of() evalúa la membresía real del usuario, fila por
-- fila. La rama del comprador exige además
-- (se.bid_mode = 'OPEN' or se.bid_opened_at is not null) — la apertura
-- SOLO habilita al comprador, nunca a un competidor, porque la rama del
-- proveedor jamás depende de bid_mode/bid_opened_at.
--
-- quotation_revisions/_items/_responses/_documents: mismo criterio, vía
-- EXISTS-join hasta quotations (mismo patrón EXISTS-a-la-tabla-padre de
-- 0043). Sin policy de update/delete en ninguna de las 4 — ya son
-- revoke update, delete (0047), la policy solo necesitaría cubrir select/
-- insert.
-- ============================================================================

alter table public.quotations enable row level security;

create policy quotations_select
  on public.quotations for select
  using (
    app.is_member_of(supplier_organization_id)
    or exists (
      select 1 from public.sourcing_events se
      where se.id = quotations.sourcing_event_id
        and app.has_permission(se.organization_id, 'quotation.read')
        and (se.bid_mode = 'OPEN' or se.bid_opened_at is not null)
    )
    or app.is_platform_admin()
  );

create policy quotations_insert
  on public.quotations for insert
  with check (
    app.is_member_of(supplier_organization_id)
    and app.has_active_sourcing_invitation(sourcing_event_id)
  );

create policy quotations_update
  on public.quotations for update
  using (app.is_member_of(supplier_organization_id))
  with check (app.is_member_of(supplier_organization_id));
-- el comprador NUNCA actualiza el contenedor del proveedor: solo lectura,
-- y solo cuando OPEN o ya abierto — ver quotations_select arriba.

create policy quotations_system_context
  on public.quotations for all
  using (app.is_system_context()) with check (app.is_system_context());


do $$
declare
  t text;
  fk text;
  tables text[] := array['quotation_items', 'quotation_responses', 'quotation_documents'];
  fks text[]    := array['quotation_revision_id', 'quotation_revision_id', 'quotation_revision_id'];
  i int;
begin
  execute 'alter table public.quotation_revisions enable row level security';
  execute format(
    'create policy quotation_revisions_select on public.quotation_revisions for select using ('
    '  exists (select 1 from public.quotations q '
    '          where q.id = quotation_revisions.quotation_id and ('
    '            app.is_member_of(q.supplier_organization_id)'
    '            or exists (select 1 from public.sourcing_events se '
    '                       where se.id = q.sourcing_event_id '
    '                         and app.has_permission(se.organization_id, ''quotation.read'') '
    '                         and (se.bid_mode = ''OPEN'' or se.bid_opened_at is not null))'
    '            or app.is_platform_admin()'
    '          ))'
    ')'
  );
  execute format(
    'create policy quotation_revisions_insert on public.quotation_revisions for insert with check ('
    '  round_type = ''INITIAL'''
    '  and exists ('
    '    select 1 from public.quotations q '
    '    join public.sourcing_event_invitations sei '
    '      on sei.sourcing_event_id = q.sourcing_event_id '
    '     and sei.supplier_organization_id = q.supplier_organization_id '
    '    where q.id = quotation_revisions.quotation_id '
    '      and app.is_member_of(q.supplier_organization_id) '
    '      and sei.status in (''INTERESTED'', ''PARTICIPATING'', ''QUOTED'') '
    '      and not exists ('
    '        select 1 from public.sourcing_event_stages st '
    '        where st.sourcing_event_id = q.sourcing_event_id and st.stage_type = ''BID_DEADLINE'''
    '          and st.scheduled_at is not null and now() > st.scheduled_at'
    '      )'
    '  )'
    ')'
  );
  execute 'create policy quotation_revisions_system_context on public.quotation_revisions for all using (app.is_system_context()) with check (app.is_system_context())';

  for i in 1..array_length(tables, 1) loop
    t := tables[i];
    fk := fks[i];
    execute format('alter table public.%I enable row level security', t);
    execute format(
      'create policy %I on public.%I for select using ('
      '  exists (select 1 from public.quotation_revisions qr '
      '          join public.quotations q on q.id = qr.quotation_id '
      '          where qr.id = %I and ('
      '            app.is_member_of(q.supplier_organization_id)'
      '            or exists (select 1 from public.sourcing_events se '
      '                       where se.id = q.sourcing_event_id '
      '                         and app.has_permission(se.organization_id, ''quotation.read'') '
      '                         and (se.bid_mode = ''OPEN'' or se.bid_opened_at is not null))'
      '            or app.is_platform_admin()'
      '          ))'
      ')', t || '_select', t, fk
    );
    execute format(
      'create policy %I on public.%I for insert with check ('
      '  exists (select 1 from public.quotation_revisions qr '
      '          join public.quotations q on q.id = qr.quotation_id '
      '          where qr.id = %I and app.is_member_of(q.supplier_organization_id))'
      ')', t || '_insert', t, fk
    );
    execute format(
      'create policy %I on public.%I for all '
      'using (app.is_system_context()) with check (app.is_system_context())',
      t || '_system_context', t
    );
  end loop;
end $$;
