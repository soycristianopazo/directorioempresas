-- ============================================================================
-- 0059 · Nuevos valores de quotation_round_type (fase 8.5)
-- ----------------------------------------------------------------------------
-- Archivo aislado, deliberado: un valor de enum recién agregado no puede
-- usarse en la misma transacción que lo agrega (restricción real de
-- Postgres), y cada .sql de este proyecto corre como una sola transacción de
-- Alembic. Cumple el compromiso textual dejado en 0047_quotations.sql:
-- "CLARIFICATION/COUNTER/BAFO pertenecen a negotiation_rounds (fase 8.5)...
-- se agregan con ALTER TYPE ... ADD VALUE cuando lleguen".
--
-- CLARIFICATION se agrega igual que los otros dos por completitud del tipo,
-- pero queda SIN CONSUMIDOR real en esta fase — negotiation_rounds (0060)
-- restringe su propio round_type a ('COUNTER','BAFO') por check. Una
-- aclaración no cambia el monto ni genera una quotation_revision nueva, así
-- que reutiliza la mensajería de fase 7 (conversations/messages) en vez de
-- una tabla dedicada — ver el comentario de 0060 para el razonamiento
-- completo.
-- ============================================================================

alter type app.quotation_round_type add value 'CLARIFICATION';
alter type app.quotation_round_type add value 'COUNTER';
alter type app.quotation_round_type add value 'BAFO';
