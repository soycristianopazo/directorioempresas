-- ============================================================================
-- 0011 · Eliminación de la auditoría forense (audit_logs)
-- ----------------------------------------------------------------------------
-- Se retira audit_logs por decisión de producto: la app no la usaba (nunca se
-- llamó a app.write_audit) y sus 24 particiones mensuales solo agregaban ruido
-- al esquema.
--
-- DROP ... CASCADE sobre la tabla particionada arrastra automáticamente:
--   · todas las particiones audit_logs_YYYY_MM
--   · sus índices
--   · sus policies de RLS (audit_logs_select_org, audit_logs_select_platform)
--   · el trigger trg_audit_logs_immutable
--
-- domain_events (el outbox transaccional) NO se toca: es un mecanismo distinto.
-- ============================================================================

drop table if exists public.audit_logs cascade;

-- Funciones que solo servían a la auditoría.
drop function if exists app.write_audit(text, text, uuid, uuid, jsonb, jsonb, text);
drop function if exists app.ensure_audit_partitions(int, int);
drop function if exists app.audit_logs_deny_mutation();
