-- ============================================================================
-- 0065 · Nuevos valores de sourcing_invitation_status (fase 8.7)
-- ----------------------------------------------------------------------------
-- Archivo aislado, mismo motivo que 0059/0064. Cumple el compromiso textual
-- dejado en 0044_sourcing_event_invitations.sql: "Los estados posteriores a
-- QUOTED del diagrama original (SHORTLISTED/NEGOTIATING/AWARDED/NOT_AWARDED)
-- dependen de evaluación y adjudicación — fase 8, no existe esa
-- infraestructura todavía". ese momento es este.
-- ============================================================================

alter type app.sourcing_invitation_status add value 'SHORTLISTED';
alter type app.sourcing_invitation_status add value 'NEGOTIATING';
alter type app.sourcing_invitation_status add value 'AWARDED';
alter type app.sourcing_invitation_status add value 'NOT_AWARDED';
