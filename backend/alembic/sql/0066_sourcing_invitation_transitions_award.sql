-- ============================================================================
-- 0066 · Transiciones de invitación para evaluación/negociación/adjudicación (fase 8.7)
-- ----------------------------------------------------------------------------
-- Nuevas filas en sourcing_event_invitation_transitions (0044) usando los
-- valores recién comprometidos en 0065. Mismo criterio de siempre:
-- transición-como-dato, is_valid_transition()/_transition() en
-- services/invitations.py deciden, nunca un UPDATE suelto de status.
--
-- SHORTLISTED→DISQUALIFIED / NEGOTIATING→DISQUALIFIED se agregan además de
-- lo listado en el plan de fase 8 — no estaban escritas explícitamente, pero
-- son la extensión mínima y consistente de la regla ya aplicada a todo
-- estado no terminal anterior a QUOTED ("cualquier estado no terminal
-- →DISQUALIFIED por el comprador"). Sin esto, un comprador no podría
-- descalificar a un proveedor ya preseleccionado o en negociación, un hueco
-- operativo real.
-- ============================================================================

insert into public.sourcing_event_invitation_transitions (from_status, to_status, label) values
  ('QUOTED',        'SHORTLISTED',   'Preseleccionar'),
  ('QUOTED',        'NEGOTIATING',   'Abrir ronda de negociación'),
  ('SHORTLISTED',   'NEGOTIATING',   'Abrir ronda de negociación'),
  ('NEGOTIATING',   'QUOTED',        'Ronda cerrada, vuelve a comparación'),
  ('QUOTED',        'AWARDED',       'Adjudicar'),
  ('SHORTLISTED',   'AWARDED',       'Adjudicar'),
  ('NEGOTIATING',   'AWARDED',       'Adjudicar'),
  ('QUOTED',        'NOT_AWARDED',   'Cierre del evento sin adjudicar a este proveedor'),
  ('SHORTLISTED',   'NOT_AWARDED',   'Cierre del evento sin adjudicar a este proveedor'),
  ('NEGOTIATING',   'NOT_AWARDED',   'Cierre del evento sin adjudicar a este proveedor'),
  ('SHORTLISTED',   'DISQUALIFIED',  'Descalificar'),
  ('NEGOTIATING',   'DISQUALIFIED',  'Descalificar')
on conflict (from_status, to_status) do nothing;
