/* =============================================================================
   BLOQUE 05 · BACKLOG, ENVEJECIMIENTO Y FLUJO
   -----------------------------------------------------------------------------
   Los KPIs de tiempo miran hacia atrás (casos ya cerrados). Este bloque mira
   el presente: qué está atascado AHORA y hace cuánto. Es la parte accionable
   del informe — la lista con la que alguien trabaja el lunes.
   ============================================================================= */


/* -----------------------------------------------------------------------------
   05.1 · BACKLOG POR ANTIGÜEDAD (WIP aging)  → GRÁFICO: barras
   Regla práctica: si el tramo ">30 días" pesa más de un 10%, hay casos
   abandonados, no lentos.
----------------------------------------------------------------------------- */
SELECT
    CASE
        WHEN DIAS_ANTIGUEDAD <  3  THEN '01 · 0-2 días'
        WHEN DIAS_ANTIGUEDAD <  8  THEN '02 · 3-7 días'
        WHEN DIAS_ANTIGUEDAD < 15  THEN '03 · 8-14 días'
        WHEN DIAS_ANTIGUEDAD < 31  THEN '04 · 15-30 días'
        WHEN DIAS_ANTIGUEDAD < 61  THEN '05 · 31-60 días'
        ELSE                            '06 · más de 60 días'
    END                                                            AS ANTIGUEDAD,
    COUNT(*)                                                       AS CASOS_ABIERTOS,
    COUNT(DISTINCT EMPRESA)                                        AS EMPRESAS,
    ROUND(AVG(DIAS_ANTIGUEDAD), 1)                                 AS DIAS_PROM
FROM V_ACRED_CASO
WHERE ESTADO_CASO = 'ABIERTO'
GROUP BY ANTIGUEDAD
ORDER BY ANTIGUEDAD;


/* -----------------------------------------------------------------------------
   05.2 · LISTA ACCIONABLE: CASOS ATASCADOS  → tabla del informe (anexo)
   Ordenada por antigüedad. Esta es la salida que se le entrega a operaciones.
----------------------------------------------------------------------------- */
SELECT
    RUT_TRABAJADOR,
    TRABAJADOR,
    CARGO,
    EMPRESA,
    MANDANTE,
    NUMERO_ACUERDO,
    F_PRIMERA_SOLICITUD,
    F_ULTIMA_SOLICITUD,
    ESTADO_ACTUAL,
    GRUPO_ACTUAL,
    F_ULTIMO_ESTADO,
    N_SOLICITUDES,
    N_RECHAZOS,
    ROUND(DIAS_ANTIGUEDAD, 0)                                      AS DIAS_ABIERTO,
    ROUND(TIMESTAMPDIFF(HOUR, F_ULTIMO_ESTADO, NOW())/24, 0)       AS DIAS_SIN_MOVIMIENTO
FROM V_ACRED_CASO
WHERE ESTADO_CASO = 'ABIERTO'
  AND DIAS_ANTIGUEDAD > 7
ORDER BY DIAS_ANTIGUEDAD DESC;


/* -----------------------------------------------------------------------------
   05.3 · SOLICITUDES SIN RESPUESTA (no tienen ningún estado terminal posterior)
   Son fugas del proceso: el trabajador solicitó y nadie cerró el ciclo.
----------------------------------------------------------------------------- */
SELECT
    ID_SOLICITUD,
    RUT_TRABAJADOR,
    TRABAJADOR,
    EMPRESA,
    MANDANTE,
    FECHA_SOLICITUD,
    FECHA_REVISION,
    NRO_CICLO,
    ROUND(TIMESTAMPDIFF(HOUR, FECHA_SOLICITUD, NOW())/24, 0)       AS DIAS_ESPERANDO
FROM V_ACRED_CICLO
WHERE FECHA_DESENLACE IS NULL
ORDER BY FECHA_SOLICITUD;


/* -----------------------------------------------------------------------------
   05.4 · FLUJO MENSUAL: ENTRADAS vs SALIDAS  → GRÁFICO: barras + línea de stock
   Si las entradas superan a las salidas mes a mes, el backlog crece y el tiempo
   de acreditación va a empeorar sí o sí en los próximos meses.
----------------------------------------------------------------------------- */
SELECT
    m.MES,
    COALESCE(ent.ENTRADAS, 0)                                      AS SOLICITUDES_NUEVAS,
    COALESCE(sal.SALIDAS, 0)                                       AS ACREDITACIONES,
    COALESCE(ent.ENTRADAS, 0) - COALESCE(sal.SALIDAS, 0)           AS VARIACION_BACKLOG
FROM (
    SELECT DISTINCT MES_SOLICITUD AS MES FROM V_ACRED_CASO WHERE MES_SOLICITUD IS NOT NULL
    UNION
    SELECT DISTINCT MES_APROBACION FROM V_ACRED_CASO WHERE MES_APROBACION IS NOT NULL
) m
LEFT JOIN (
    SELECT MES_SOLICITUD AS MES, COUNT(*) AS ENTRADAS
    FROM V_ACRED_CASO WHERE MES_SOLICITUD IS NOT NULL GROUP BY MES_SOLICITUD
) ent ON ent.MES = m.MES
LEFT JOIN (
    SELECT MES_APROBACION AS MES, COUNT(*) AS SALIDAS
    FROM V_ACRED_CASO WHERE MES_APROBACION IS NOT NULL GROUP BY MES_APROBACION
) sal ON sal.MES = m.MES
ORDER BY m.MES;


/* -----------------------------------------------------------------------------
   05.5 · EMBUDO DEL PROCESO  → GRÁFICO: funnel
----------------------------------------------------------------------------- */
SELECT '1 · Trabajadores asignados a contrato' AS ETAPA, 1 AS ORDEN,
       COUNT(*) AS CANTIDAD
FROM DB_LEGAV_ASIG_PERSONAL_ACUERDO
UNION ALL
SELECT '2 · Con al menos una solicitud', 2, COUNT(DISTINCT ID_ASIGNACION)
FROM DB_LEGAV_SOLICITUD_ACREDITACION
UNION ALL
SELECT '3 · Con al menos una revisión', 3, COUNT(DISTINCT ID_ASIGNACION)
FROM V_ACRED_CICLO WHERE FECHA_DESENLACE IS NOT NULL
UNION ALL
SELECT '4 · Acreditados alguna vez', 4, COUNT(*)
FROM V_ACRED_CASO WHERE ESTADO_CASO = 'CERRADO'
UNION ALL
SELECT '5 · Acreditados y vigentes hoy', 5, COUNT(*)
FROM V_ACRED_CASO WHERE GRUPO_ACTUAL = 'APROBADO'
ORDER BY ORDEN;


/* -----------------------------------------------------------------------------
   05.6 · MATRIZ ESTADO ACTUAL × EMPRESA  → GRÁFICO: barras apiladas 100%
----------------------------------------------------------------------------- */
SELECT
    EMPRESA,
    COUNT(*)                                                       AS TOTAL,
    SUM(GRUPO_ACTUAL = 'APROBADO')                                 AS APROBADOS,
    SUM(GRUPO_ACTUAL = 'RECHAZADO')                                AS RECHAZADOS,
    SUM(GRUPO_ACTUAL = 'EN_PROCESO')                               AS EN_PROCESO,
    SUM(GRUPO_ACTUAL = 'BAJA')                                     AS BAJAS,
    SUM(GRUPO_ACTUAL IN ('SIN_ESTADO','OTRO'))                     AS SIN_CLASIFICAR,
    ROUND(100 * SUM(GRUPO_ACTUAL = 'APROBADO') / COUNT(*), 1)      AS PCT_VIGENTE
FROM V_ACRED_CASO
GROUP BY EMPRESA
HAVING COUNT(*) >= 5
ORDER BY TOTAL DESC;
