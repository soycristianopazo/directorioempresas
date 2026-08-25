-- ============================================================================
-- 0074 · Fix: recursión infinita en RLS de negociación (fase 8.5)
-- ----------------------------------------------------------------------------
-- Bug real encontrado en vivo (suite de tests, no en el dry-run de
-- migraciones): "infinite recursion detected in policy for relation
-- negotiation_round_participants" al ejecutar cualquier consulta que uniera
-- negotiation_rounds con negotiation_round_participants.
--
-- Causa: 0061_fase8_rls_negotiation.sql define un ciclo entre dos policies —
-- negotiation_rounds_select hace un EXISTS directo contra
-- negotiation_round_participants (para la rama del proveedor participante),
-- y negotiation_round_participants_select hace un EXISTS directo contra
-- negotiation_rounds (para la rama del comprador). Evaluar la policy de una
-- tabla dispara la evaluación de la policy de la otra, que vuelve a
-- disparar la primera, indefinidamente. Exactamente el mismo bug ya
-- documentado para conversation_participants en 0052
-- (docs/RLS.md/"gotchas de fase 7", bug #6) — un EXISTS escrito directo
-- contra una tabla cuya propia policy referencia de vuelta a la tabla de
-- origen.
--
-- Fix: mismo patrón que app.is_conversation_participant() en 0052 — una
-- función SECURITY DEFINER STABLE rompe el ciclo porque su consulta interna
-- corre con los privilegios del dueño de la función (no sujeto a RLS, sin
-- FORCE ROW LEVEL SECURITY en este proyecto — 0010_hardening.sql), así que
-- nunca vuelve a evaluar la policy que la está llamando. Basta con envolver
-- UN lado del ciclo: al hacerlo, negotiation_rounds_select ya no dispara una
-- evaluación de RLS sobre negotiation_round_participants, así que la
-- referencia inversa (negotiation_round_participants_select →
-- negotiation_rounds) deja de recursar también.
-- ============================================================================

create or replace function app.is_negotiation_round_participant(p_negotiation_round_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.negotiation_round_participants nrp
    where nrp.negotiation_round_id = p_negotiation_round_id
      and app.is_member_of(nrp.supplier_organization_id)
  );
$$;

grant execute on function app.is_negotiation_round_participant(uuid) to app_user;

comment on function app.is_negotiation_round_participant(uuid) is
  '¿Alguna organización del usuario actual participa en esta ronda de negociación? SECURITY DEFINER a propósito — rompe la recursión de RLS entre negotiation_rounds y negotiation_round_participants (ver encabezado de esta migración), mismo criterio que app.is_conversation_participant() en 0052.';


drop policy negotiation_rounds_select on public.negotiation_rounds;

create policy negotiation_rounds_select
  on public.negotiation_rounds for select
  using (
    exists (
      select 1 from public.sourcing_events se
      where se.id = sourcing_event_id and app.has_permission(se.organization_id, 'negotiation.manage')
    )
    or app.is_negotiation_round_participant(id)
  );
