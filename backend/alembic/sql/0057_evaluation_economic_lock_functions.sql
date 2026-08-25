-- ============================================================================
-- 0057 · Bloqueo económico del comité de evaluación (fase 8.3/8.4)
-- ----------------------------------------------------------------------------
-- La migración más revisada de esta fase — equivalente en criticidad a
-- 0049_fase7_rls_quotations.sql. Ver plan de fase 8, Decisión 1.
--
-- Postgres RLS es estrictamente a nivel de FILA, nunca de columna (confirmado
-- explorando las únicas dos vistas de este proyecto, ambas
-- security_invoker=true, sin precedente de ocultar columnas dentro de una
-- fila visible). "Un evaluador técnico nunca ve montos" es intrínsecamente
-- columnar — una policy nueva sobre quotation_items/quotation_revisions
-- daría la fila entera o nada. Además EVALUATOR no tiene quotation.read
-- (confirmado por grep de 0009_seed_roles_permissions.sql), así que el
-- patrón sellado de 0049 (que NO se toca en esta migración) rechazaría a
-- cualquier evaluador de plano.
--
-- Solución: todo acceso de un evaluador a datos de cotización pasa por estas
-- cuatro funciones, cada una con PROYECCIÓN EXPLÍCITA de columnas (nunca
-- select *) y el filtro de autorización escrito en el propio cuerpo, contra
-- evaluation_assignments (0055) exigiendo que la asignación sea DEL USUARIO
-- ACTUAL específico — no basta con "alguien de la organización tiene una
-- asignación", tiene que ser la asignación de ESE evaluador (organization_
-- members.user_id = app.current_user_id(), nunca solo is_member_of(), que
-- dejaría ver a cualquier comprador de la organización).
--
-- Alcance de lectura: solo la REVISIÓN VIGENTE (quotations.current_revision_
-- id) — el comité evalúa el estado actual de la oferta, no su historial de
-- borradores. La vista comercial (revisiones) es la única excepción: ve
-- TODAS las revisiones (incluidas rondas de negociación futuras, fase 8.5),
-- porque comparar la evolución de precio ronda a ronda es el propósito de
-- esa vista.
--
-- La vista comercial además reutiliza, DENTRO del cuerpo de su propia
-- función, la regla de apertura ya sagrada desde fase 7:
-- (se.bid_mode = 'OPEN' or se.bid_opened_at is not null). La apertura de
-- sobre es el corte natural que ya existe — no se inventa un flag nuevo de
-- "cierre de fase técnica".
--
-- Nota de riesgo aceptada, no una omisión: list_quotation_documents_for_
-- technical_evaluation expone el PDF en sí (nombre + storage_path), y un PDF
-- es un blob opaco — no hay forma de garantizar que un proveedor no haya
-- subido un adjunto con precios adentro. Es el mismo riesgo que el propio
-- COMPRADOR ya acepta hoy antes de la apertura (quotation_documents_select
-- en 0049 usa la misma regla de corte) — extender el mismo límite de
-- confianza al evaluador técnico bajo idéntica condición de asignación no es
-- un agujero nuevo, es el límite ya existente aplicado a un lector más.
-- ============================================================================


create or replace function app.list_quotation_items_for_technical_evaluation(
  p_sourcing_event_id uuid
)
returns table (
  item_id                  uuid,
  quotation_id             uuid,
  supplier_organization_id uuid,
  sourcing_event_item_id   uuid,
  quantity                 numeric,
  unit_code                text,
  lead_time_days           int,
  brand                    text,
  model                    text,
  notes                    text
)
language sql
stable
security definer
set search_path = ''
as $$
  select
    qi.id, q.id, q.supplier_organization_id, qi.sourcing_event_item_id,
    qi.quantity, qi.unit_code, qi.lead_time_days, qi.brand, qi.model, qi.notes
  from public.quotation_items qi
  join public.quotation_revisions qr on qr.id = qi.quotation_revision_id
  join public.quotations q on q.id = qr.quotation_id and q.current_revision_id = qr.id
  where q.sourcing_event_id = p_sourcing_event_id
    and exists (
      select 1
      from public.evaluation_assignments ea
      join public.organization_members om on om.id = ea.organization_member_id
      where ea.sourcing_event_id = p_sourcing_event_id
        and om.user_id = app.current_user_id()
    );
$$;

grant execute on function app.list_quotation_items_for_technical_evaluation(uuid) to app_user;

comment on function app.list_quotation_items_for_technical_evaluation(uuid) is
  'Líneas de la revisión vigente de cada cotización del evento, SIN unit_price/discount_pct/tax_rate/line_total, para cualquier evaluador con asignación en el evento (técnico o comercial — la restricción de montos está en no proyectar esas columnas, no en can_view_commercial, porque un evaluador comercial también necesita ver las líneas no monetarias).';


create or replace function app.list_quotation_responses_for_technical_evaluation(
  p_sourcing_event_id uuid
)
returns table (
  response_id                  uuid,
  quotation_id                 uuid,
  supplier_organization_id     uuid,
  sourcing_event_criterion_id  uuid,
  complies                     boolean,
  value_text                   text,
  notes                        text
)
language sql
stable
security definer
set search_path = ''
as $$
  select
    qr2.id, q.id, q.supplier_organization_id, qr2.sourcing_event_criterion_id,
    qr2.complies, qr2.value_text, qr2.notes
  from public.quotation_responses qr2
  join public.quotation_revisions qr on qr.id = qr2.quotation_revision_id
  join public.quotations q on q.id = qr.quotation_id and q.current_revision_id = qr.id
  where q.sourcing_event_id = p_sourcing_event_id
    and exists (
      select 1
      from public.evaluation_assignments ea
      join public.organization_members om on om.id = ea.organization_member_id
      where ea.sourcing_event_id = p_sourcing_event_id
        and om.user_id = app.current_user_id()
    );
$$;

grant execute on function app.list_quotation_responses_for_technical_evaluation(uuid) to app_user;

comment on function app.list_quotation_responses_for_technical_evaluation(uuid) is
  'Respuestas del proveedor a sourcing_event_criteria de la revisión vigente — no monetario, pero sin policy de fila para un evaluador hoy (EVALUATOR no tiene quotation.read). Mismo alcance/autorización que list_quotation_items_for_technical_evaluation.';


create or replace function app.list_quotation_documents_for_technical_evaluation(
  p_sourcing_event_id uuid
)
returns table (
  document_id               uuid,
  quotation_id              uuid,
  supplier_organization_id  uuid,
  name                      text,
  storage_path              text,
  created_at                timestamptz
)
language sql
stable
security definer
set search_path = ''
as $$
  select
    qd.id, q.id, q.supplier_organization_id, qd.name, qd.storage_path, qd.created_at
  from public.quotation_documents qd
  join public.quotation_revisions qr on qr.id = qd.quotation_revision_id
  join public.quotations q on q.id = qr.quotation_id and q.current_revision_id = qr.id
  where q.sourcing_event_id = p_sourcing_event_id
    and exists (
      select 1
      from public.evaluation_assignments ea
      join public.organization_members om on om.id = ea.organization_member_id
      where ea.sourcing_event_id = p_sourcing_event_id
        and om.user_id = app.current_user_id()
    );
$$;

grant execute on function app.list_quotation_documents_for_technical_evaluation(uuid) to app_user;

comment on function app.list_quotation_documents_for_technical_evaluation(uuid) is
  'Adjuntos de la revisión vigente, visibles a cualquier evaluador asignado al evento. Riesgo residual aceptado y documentado en el encabezado de este archivo: un PDF puede contener precios, igual que ya acepta el comprador antes de la apertura.';


create or replace function app.list_quotation_revisions_for_commercial_evaluation(
  p_sourcing_event_id uuid
)
returns table (
  revision_id               uuid,
  quotation_id              uuid,
  supplier_organization_id  uuid,
  round_number              int,
  round_type                text,
  submitted_at              timestamptz,
  valid_until               date,
  currency_code             char(3),
  fx_rate_snapshot          numeric,
  subtotal                  numeric,
  tax_amount                numeric,
  total_amount              numeric,
  total_amount_base         numeric,
  payment_terms             text,
  delivery_days             int,
  warranty_terms            text,
  exclusions                text,
  notes                     text
)
language sql
stable
security definer
set search_path = ''
as $$
  select
    qr.id, q.id, q.supplier_organization_id, qr.round_number, qr.round_type::text,
    qr.submitted_at, qr.valid_until, qr.currency_code, qr.fx_rate_snapshot,
    qr.subtotal, qr.tax_amount, qr.total_amount, qr.total_amount_base,
    qr.payment_terms, qr.delivery_days, qr.warranty_terms, qr.exclusions, qr.notes
  from public.quotation_revisions qr
  join public.quotations q on q.id = qr.quotation_id
  where q.sourcing_event_id = p_sourcing_event_id
    and exists (
      select 1
      from public.evaluation_assignments ea
      join public.organization_members om on om.id = ea.organization_member_id
      where ea.sourcing_event_id = p_sourcing_event_id
        and om.user_id = app.current_user_id()
        and ea.can_view_commercial = true
    )
    and exists (
      select 1 from public.sourcing_events se
      where se.id = p_sourcing_event_id
        and (se.bid_mode = 'OPEN' or se.bid_opened_at is not null)
    );
$$;

grant execute on function app.list_quotation_revisions_for_commercial_evaluation(uuid) to app_user;

comment on function app.list_quotation_revisions_for_commercial_evaluation(uuid) is
  'TODAS las revisiones (histórico completo, incluidas rondas de negociación) con montos — exige can_view_commercial=true Y la misma regla de apertura de sobre que 0049 (bid_mode=OPEN o bid_opened_at). Antes de la apertura, un evaluador comercial recibe 0 filas aunque su asignación ya exista.';
