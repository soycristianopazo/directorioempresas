-- ============================================================================
-- 0053 · Secuencia real para sourcing_events.event_code — bug de fase 6
-- encontrado en vivo durante la verificación de fase 7
-- ----------------------------------------------------------------------------
-- repositories/sourcing.py::next_event_code() generaba el correlativo con
-- `select count(*) from sourcing_events where event_code like '%-{year}-%'`,
-- corrido dentro de la sesión RLS-scoped del usuario que llama — pero
-- sourcing_events.select solo devuelve las filas de SU organización
-- (0043_fase6_rls.sql), así que ese count() es, sin querer, por organización,
-- mientras que `event_code` es UNIQUE a nivel de tabla completa. Dos
-- organizaciones distintas creando cada una su primer RFQ del año generan
-- ambas "RFQ-2026-0001" y la segunda revienta con UniqueViolationError.
-- Encontrado dos veces de forma independiente: por tests/test_quotations.py
-- (varias organizaciones de prueba en la misma corrida) y por verificación
-- manual en el navegador (un evento nuevo sobre datos ya sembrados).
--
-- Una secuencia de Postgres no está sujeta a RLS (no es una tabla) y
-- nextval() es atómica — resuelve la colisión entre organizaciones Y la
-- condición de carrera propia de "contar y luego insertar" en un solo
-- movimiento. Cambio de comportamiento menor y aceptado: el correlativo dentro
-- del código ya no reinicia en 0001 cada año (sigue subiendo) — el año en el
-- propio código (`RFQ-2026-0142`) sigue siendo el dato real de cuándo se creó,
-- el número ya no pretende ser "el 142° de este año".
-- ============================================================================

create sequence public.sourcing_event_code_seq;

comment on sequence public.sourcing_event_code_seq is
  'Correlativo real para sourcing_events.event_code — reemplaza el count(*) racy y RLS-scoped que rompía entre organizaciones distintas. Ver repositories/sourcing.py::next_event_code().';

-- Una secuencia nueva arranca en 1 sin importar qué ya exista en la tabla —
-- si YA hay filas con sufijo numérico (sembradas a mano, o creadas antes de
-- este fix con el count() viejo), el primer nextval() colisiona igual contra
-- el UNIQUE existente. Se adelanta el arranque al máximo sufijo ya usado.
-- Encontrado en vivo: exactamente este caso, un evento real creado desde el
-- navegador antes de aplicar esta migración ya ocupaba "...-0001".
do $$
declare
  v_max int;
begin
  select coalesce(max(substring(event_code from '(\d+)$')::int), 0)
    into v_max
    from public.sourcing_events;

  if v_max > 0 then
    perform setval('public.sourcing_event_code_seq', v_max);
  end if;
end $$;
