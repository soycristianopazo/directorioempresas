-- ============================================================================
-- 0064 · Nuevos valores de sourcing_event_status (fase 8.7)
-- ----------------------------------------------------------------------------
-- Archivo aislado, mismo motivo que 0059: un valor de enum recién agregado
-- no puede usarse en la misma transacción que lo agrega. Cumple el
-- compromiso textual dejado en 0040_sourcing_events.sql: "el enum se
-- extiende hacia adelante... no se inventan estados que nada puede alcanzar
-- hoy" — AWARDED/CLOSED es exactamente esa extensión, ahora que awards
-- (0062) y el cierre de evento (services/sourcing.py::close_event(),
-- disparado por services/awards.py::publish_award()) existen.
-- ============================================================================

alter type app.sourcing_event_status add value 'AWARDED';
alter type app.sourcing_event_status add value 'CLOSED';
