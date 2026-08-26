-- ============================================================================
-- 0081 · Nuevo valor VOID en sourcing_event_status (fase 10)
-- ----------------------------------------------------------------------------
-- Archivo aislado, mismo motivo que 0059/0064: un valor de enum recién
-- agregado no puede usarse en la misma transacción que lo agrega.
--
-- "Desierta": el comprador declara manualmente que ninguna cotización
-- calificó — no hay corredor de tareas programadas en el backend que pueda
-- disparar esto solo al vencer un plazo, así que es una acción explícita
-- (services/sourcing.py::declare_void()), no automática. Solo alcanzable
-- desde PUBLISHED (mismo criterio de exclusión mutua que AWARDED/CLOSED en
-- 0064: close_event() ya saca al evento de PUBLISHED apenas se publica un
-- award, así que VOID y AWARDED/CLOSED nunca compiten por el mismo evento).
-- ============================================================================

alter type app.sourcing_event_status add value 'VOID';

alter table public.sourcing_events add column void_reason text;
