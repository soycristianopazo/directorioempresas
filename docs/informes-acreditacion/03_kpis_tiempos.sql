/* =============================================================================
   BLOQUE 03 · KPIs DE TIEMPOS DE ACREDITACIÓN   ★ el núcleo del informe ★
   -----------------------------------------------------------------------------
   NOTA METODOLÓGICA: en procesos documentales la media MIENTE. Cuatro casos
   atascados 90 días arrastran el promedio de cientos que se resuelven en 2.
   Por eso todas las queries devuelven MEDIANA (P50) y P90 junto al promedio.
   El P90 es el número que hay que llevar a comité: "9 de cada 10 se acreditan
   en X días o menos".

   MySQL 5.7 no tiene PERCENTILE_CONT, así que se calcula con el truco
   GROUP_CONCAT + SUBSTRING_INDEX. Requiere subir el límite de concatenación:
   ============================================================================= */

SET SESSION group_concat_max_len = 10000000;


/* -----------------------------------------------------------------------------
   03.1 · TARJETA RESUMEN (los números de portada del informe)
----------------------------------------------------------------------------- */
SELECT
    COUNT(*)                                                       AS CASOS_TOTALES,
    SUM(ESTADO_CASO = 'CERRADO')                                   AS ACREDITADOS,
    SUM(ESTADO_CASO = 'ABIERTO')                                   AS EN_PROCESO,
    ROUND(100 * SUM(ESTADO_CASO = 'CERRADO') / COUNT(*), 1)        AS PCT_ACREDITACION,
    ROUND(AVG(DIAS_TOTAL), 2)                                      AS PROMEDIO_DIAS,
    CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(
        GROUP_CONCAT(DIAS_TOTAL ORDER BY DIAS_TOTAL SEPARATOR ','),
        ',', GREATEST(1, CEILING(COUNT(DIAS_TOTAL) * 0.50))), ',', -1)
        AS DECIMAL(10,2))                                          AS MEDIANA_DIAS,
    CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(
        GROUP_CONCAT(DIAS_TOTAL ORDER BY DIAS_TOTAL SEPARATOR ','),
        ',', GREATEST(1, CEILING(COUNT(DIAS_TOTAL) * 0.90))), ',', -1)
        AS DECIMAL(10,2))                                          AS P90_DIAS,
    MIN(DIAS_TOTAL)                                                AS MIN_DIAS,
    MAX(DIAS_TOTAL)                                                AS MAX_DIAS,
    ROUND(AVG(N_SOLICITUDES), 2)                                   AS ENVIOS_PROMEDIO,
    ROUND(100 * SUM(N_SOLICITUDES > 1) / COUNT(*), 1)              AS PCT_CON_RETRABAJO,
    ROUND(AVG(DIAS_EN_MANDANTE), 2)                                AS PROM_DIAS_MANDANTE,
    ROUND(AVG(DIAS_EN_CONTRATISTA), 2)                             AS PROM_DIAS_CONTRATISTA
FROM V_ACRED_CASO;


/* -----------------------------------------------------------------------------
   03.2 · EVOLUCIÓN MENSUAL   → GRÁFICO: líneas (P50 / P90) + barras (volumen)
   Es el gráfico que abre el informe: muestra si el proceso mejora o se degrada.
----------------------------------------------------------------------------- */
SELECT
    MES_SOLICITUD                                                  AS MES,
    COUNT(*)                                                       AS SOLICITUDES,
    SUM(ESTADO_CASO = 'CERRADO')                                   AS ACREDITADOS,
    ROUND(100 * SUM(ESTADO_CASO = 'CERRADO') / COUNT(*), 1)        AS PCT_CIERRE,
    ROUND(AVG(DIAS_TOTAL), 2)                                      AS PROMEDIO_DIAS,
    CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(
        GROUP_CONCAT(DIAS_TOTAL ORDER BY DIAS_TOTAL SEPARATOR ','),
        ',', GREATEST(1, CEILING(COUNT(DIAS_TOTAL) * 0.50))), ',', -1)
        AS DECIMAL(10,2))                                          AS MEDIANA_DIAS,
    CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(
        GROUP_CONCAT(DIAS_TOTAL ORDER BY DIAS_TOTAL SEPARATOR ','),
        ',', GREATEST(1, CEILING(COUNT(DIAS_TOTAL) * 0.90))), ',', -1)
        AS DECIMAL(10,2))                                          AS P90_DIAS,
    ROUND(AVG(N_SOLICITUDES), 2)                                   AS ENVIOS_PROMEDIO
FROM V_ACRED_CASO
WHERE MES_SOLICITUD IS NOT NULL
GROUP BY MES_SOLICITUD
ORDER BY MES_SOLICITUD;


/* -----------------------------------------------------------------------------
   03.3 · RANKING POR EMPRESA CONTRATISTA  → GRÁFICO: barras horizontales
   Se filtran empresas con <5 casos: con 2 casos no hay estadística, hay anécdota.
----------------------------------------------------------------------------- */
SELECT
    EMPRESA,
    COUNT(*)                                                       AS CASOS,
    SUM(ESTADO_CASO = 'CERRADO')                                   AS ACREDITADOS,
    ROUND(100 * SUM(ESTADO_CASO = 'CERRADO') / COUNT(*), 1)        AS PCT_CIERRE,
    ROUND(AVG(DIAS_TOTAL), 2)                                      AS PROMEDIO_DIAS,
    CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(
        GROUP_CONCAT(DIAS_TOTAL ORDER BY DIAS_TOTAL SEPARATOR ','),
        ',', GREATEST(1, CEILING(COUNT(DIAS_TOTAL) * 0.50))), ',', -1)
        AS DECIMAL(10,2))                                          AS MEDIANA_DIAS,
    CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(
        GROUP_CONCAT(DIAS_TOTAL ORDER BY DIAS_TOTAL SEPARATOR ','),
        ',', GREATEST(1, CEILING(COUNT(DIAS_TOTAL) * 0.90))), ',', -1)
        AS DECIMAL(10,2))                                          AS P90_DIAS,
    ROUND(AVG(N_SOLICITUDES), 2)                                   AS ENVIOS_PROMEDIO,
    ROUND(AVG(N_RECHAZOS), 2)                                      AS RECHAZOS_PROMEDIO,
    ROUND(AVG(DIAS_EN_MANDANTE), 2)                                AS DIAS_MANDANTE,
    ROUND(AVG(DIAS_EN_CONTRATISTA), 2)                             AS DIAS_CONTRATISTA
FROM V_ACRED_CASO
GROUP BY EMPRESA
HAVING COUNT(*) >= 5
ORDER BY MEDIANA_DIAS DESC;


/* -----------------------------------------------------------------------------
   03.4 · POR MANDANTE / FAENA / GERENCIA  → tabla comparativa
----------------------------------------------------------------------------- */
SELECT
    MANDANTE,
    COALESCE(GERENCIA, '(sin gerencia)')                           AS GERENCIA,
    COUNT(*)                                                       AS CASOS,
    ROUND(100 * SUM(ESTADO_CASO = 'CERRADO') / COUNT(*), 1)        AS PCT_CIERRE,
    ROUND(AVG(DIAS_TOTAL), 2)                                      AS PROMEDIO_DIAS,
    CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(
        GROUP_CONCAT(DIAS_TOTAL ORDER BY DIAS_TOTAL SEPARATOR ','),
        ',', GREATEST(1, CEILING(COUNT(DIAS_TOTAL) * 0.50))), ',', -1)
        AS DECIMAL(10,2))                                          AS MEDIANA_DIAS,
    CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(
        GROUP_CONCAT(DIAS_TOTAL ORDER BY DIAS_TOTAL SEPARATOR ','),
        ',', GREATEST(1, CEILING(COUNT(DIAS_TOTAL) * 0.90))), ',', -1)
        AS DECIMAL(10,2))                                          AS P90_DIAS
FROM V_ACRED_CASO
GROUP BY MANDANTE, GERENCIA
ORDER BY CASOS DESC;


/* -----------------------------------------------------------------------------
   03.5 · DISTRIBUCIÓN DE TIEMPOS  → GRÁFICO: histograma
   Muestra la forma real del proceso, no solo su centro.
----------------------------------------------------------------------------- */
SELECT
    CASE
        WHEN DIAS_TOTAL IS NULL THEN '99 · sin aprobar'
        WHEN DIAS_TOTAL <  1    THEN '01 · mismo día'
        WHEN DIAS_TOTAL <  2    THEN '02 · 1 día'
        WHEN DIAS_TOTAL <  4    THEN '03 · 2-3 días'
        WHEN DIAS_TOTAL <  8    THEN '04 · 4-7 días'
        WHEN DIAS_TOTAL < 15    THEN '05 · 8-14 días'
        WHEN DIAS_TOTAL < 31    THEN '06 · 15-30 días'
        ELSE                         '07 · más de 30 días'
    END                                                            AS TRAMO,
    COUNT(*)                                                       AS CASOS,
    ROUND(100 * COUNT(*) / (SELECT COUNT(*) FROM V_ACRED_CASO), 1) AS PCT
FROM V_ACRED_CASO
GROUP BY TRAMO
ORDER BY TRAMO;


/* -----------------------------------------------------------------------------
   03.6 · CUMPLIMIENTO DE SLA  → GRÁFICO: barras apiladas por mes
   ⚠ Ajustar @SLA_DIAS al compromiso real del contrato. Por defecto: 5 días.
----------------------------------------------------------------------------- */
SET @SLA_DIAS = 5;

SELECT
    MES_SOLICITUD                                                  AS MES,
    COUNT(*)                                                       AS CASOS_CERRADOS,
    SUM(DIAS_TOTAL <= @SLA_DIAS)                                   AS DENTRO_SLA,
    SUM(DIAS_TOTAL >  @SLA_DIAS)                                   AS FUERA_SLA,
    ROUND(100 * SUM(DIAS_TOTAL <= @SLA_DIAS) / COUNT(*), 1)        AS PCT_CUMPLIMIENTO,
    ROUND(AVG(CASE WHEN DIAS_TOTAL > @SLA_DIAS
                   THEN DIAS_TOTAL - @SLA_DIAS END), 2)            AS DIAS_EXCESO_PROMEDIO
FROM V_ACRED_CASO
WHERE ESTADO_CASO = 'CERRADO' AND MES_SOLICITUD IS NOT NULL
GROUP BY MES_SOLICITUD
ORDER BY MES_SOLICITUD;


/* -----------------------------------------------------------------------------
   03.7 · ¿DÓNDE SE VA EL TIEMPO?  → GRÁFICO: barras apiladas 100%
   Descompone el lead time en tres tramos con dueño distinto. Es el análisis que
   corta la discusión de "la culpa es del mandante" vs "la culpa es de la EECC".
----------------------------------------------------------------------------- */
SELECT
    'Preparación documental (EECC, antes de solicitar)' AS TRAMO, 1 AS ORDEN,
    ROUND(AVG(DIAS_PREPARACION), 2)   AS DIAS_PROMEDIO, COUNT(DIAS_PREPARACION) AS CASOS
FROM V_ACRED_CASO WHERE DIAS_PREPARACION >= 0
UNION ALL
SELECT 'Revisión (mandante / acreditador)', 2,
    ROUND(AVG(DIAS_EN_MANDANTE), 2), COUNT(DIAS_EN_MANDANTE)
FROM V_ACRED_CASO WHERE DIAS_EN_MANDANTE >= 0
UNION ALL
SELECT 'Corrección y reenvío (EECC, tras rechazo)', 3,
    ROUND(AVG(DIAS_EN_CONTRATISTA), 2), COUNT(DIAS_EN_CONTRATISTA)
FROM V_ACRED_CASO WHERE DIAS_EN_CONTRATISTA >= 0
ORDER BY ORDEN;


/* -----------------------------------------------------------------------------
   03.8 · SLA POR CICLO INDIVIDUAL  → cuánto tarda el acreditador en responder
   Este es el KPI de gestión del equipo de acreditación (aislado del retrabajo).
----------------------------------------------------------------------------- */
SELECT
    MES_SOLICITUD                                                  AS MES,
    COUNT(*)                                                       AS CICLOS,
    SUM(RESULTADO_CICLO = 'APROBADO')                              AS APROBADOS,
    SUM(RESULTADO_CICLO = 'RECHAZADO')                             AS RECHAZADOS,
    SUM(FECHA_DESENLACE IS NULL)                                   AS SIN_RESPUESTA,
    ROUND(100 * SUM(RESULTADO_CICLO = 'APROBADO') / COUNT(*), 1)   AS PCT_APROBACION_1RA,
    ROUND(AVG(DIAS_CICLO), 2)                                      AS PROMEDIO_DIAS_RESPUESTA,
    CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(
        GROUP_CONCAT(DIAS_CICLO ORDER BY DIAS_CICLO SEPARATOR ','),
        ',', GREATEST(1, CEILING(COUNT(DIAS_CICLO) * 0.50))), ',', -1)
        AS DECIMAL(10,2))                                          AS MEDIANA_DIAS_RESPUESTA,
    CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(
        GROUP_CONCAT(DIAS_CICLO ORDER BY DIAS_CICLO SEPARATOR ','),
        ',', GREATEST(1, CEILING(COUNT(DIAS_CICLO) * 0.90))), ',', -1)
        AS DECIMAL(10,2))                                          AS P90_DIAS_RESPUESTA
FROM V_ACRED_CICLO
WHERE MES_SOLICITUD IS NOT NULL
GROUP BY MES_SOLICITUD
ORDER BY MES_SOLICITUD;


/* -----------------------------------------------------------------------------
   03.9 · CARGA Y DESEMPEÑO POR REVISOR  → tabla + barras
   Cruzar volumen con tiempo: un revisor lento con 800 casos no es el mismo
   problema que uno lento con 12.
----------------------------------------------------------------------------- */
SELECT
    COALESCE(REVISOR, '(sin revisor asignado)')                    AS REVISOR,
    COUNT(*)                                                       AS CICLOS_RESUELTOS,
    SUM(RESULTADO_CICLO = 'APROBADO')                              AS APROBO,
    SUM(RESULTADO_CICLO = 'RECHAZADO')                             AS RECHAZO,
    ROUND(100 * SUM(RESULTADO_CICLO = 'RECHAZADO') / COUNT(*), 1)  AS TASA_RECHAZO,
    ROUND(AVG(DIAS_CICLO), 2)                                      AS PROMEDIO_DIAS,
    CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(
        GROUP_CONCAT(DIAS_CICLO ORDER BY DIAS_CICLO SEPARATOR ','),
        ',', GREATEST(1, CEILING(COUNT(DIAS_CICLO) * 0.50))), ',', -1)
        AS DECIMAL(10,2))                                          AS MEDIANA_DIAS,
    COUNT(DISTINCT EMPRESA)                                        AS EMPRESAS_ATENDIDAS,
    MIN(FECHA_DESENLACE)                                           AS PRIMERA_REVISION,
    MAX(FECHA_DESENLACE)                                           AS ULTIMA_REVISION
FROM V_ACRED_CICLO
WHERE FECHA_DESENLACE IS NOT NULL
GROUP BY REVISOR
ORDER BY CICLOS_RESUELTOS DESC;


/* -----------------------------------------------------------------------------
   03.10 · ESTACIONALIDAD  → GRÁFICO: heatmap día de semana × hora
   Detecta si los cuellos de botella son de capacidad o de horario de atención.
----------------------------------------------------------------------------- */
SELECT
    DAYOFWEEK(FECHA_SOLICITUD)                                     AS ORDEN_DIA,
    DIA_SEMANA_SOLICITUD                                           AS DIA,
    HORA_SOLICITUD                                                 AS HORA,
    COUNT(*)                                                       AS SOLICITUDES,
    ROUND(AVG(DIAS_CICLO), 2)                                      AS DIAS_RESPUESTA_PROM
FROM V_ACRED_CICLO
GROUP BY ORDEN_DIA, DIA, HORA
ORDER BY ORDEN_DIA, HORA;


/* -----------------------------------------------------------------------------
   03.11 · COLA vs TRABAJO EFECTIVO  → GRÁFICO: barras apiladas por mes
   ★ Habilitado por el estado "En Revisión" (id 1) del catálogo real. ★

   Parte el tiempo de revisión en dos:
     · DIAS_EN_COLA          = solicitud → alguien la toma  (problema de CAPACIDAD)
     · DIAS_TRABAJO_EFECTIVO = tomada    → resuelta         (problema de COMPLEJIDAD)

   La lectura es directa y define la acción:
     cola alta  → faltan revisores o falta priorización de la bandeja
     trabajo alto → el expediente es difícil, o falta criterio/estándar claro
   Sumar ambos sin distinguir es lo que hace que se contrate gente cuando el
   problema era el criterio, o al revés.
----------------------------------------------------------------------------- */
SELECT
    MES_SOLICITUD                                                  AS MES,
    COUNT(*)                                                       AS CICLOS,
    COUNT(FECHA_EN_REVISION)                                       AS CON_TOMA_REGISTRADA,
    ROUND(AVG(DIAS_EN_COLA), 2)                                    AS PROM_DIAS_COLA,
    ROUND(AVG(DIAS_TRABAJO_EFECTIVO), 2)                           AS PROM_DIAS_TRABAJO,
    ROUND(AVG(DIAS_CICLO), 2)                                      AS PROM_DIAS_TOTAL,
    ROUND(100 * AVG(DIAS_EN_COLA)
              / NULLIF(AVG(DIAS_CICLO), 0), 1)                     AS PCT_TIEMPO_EN_COLA,
    CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(
        GROUP_CONCAT(DIAS_EN_COLA ORDER BY DIAS_EN_COLA SEPARATOR ','),
        ',', GREATEST(1, CEILING(COUNT(DIAS_EN_COLA) * 0.90))), ',', -1)
        AS DECIMAL(10,2))                                          AS P90_DIAS_COLA
FROM V_ACRED_CICLO
WHERE MES_SOLICITUD IS NOT NULL
GROUP BY MES_SOLICITUD
ORDER BY MES_SOLICITUD;


/* -----------------------------------------------------------------------------
   03.12 · COLA vs TRABAJO POR REVISOR
   Distingue al revisor que tiene la bandeja llena del que se demora en resolver.
----------------------------------------------------------------------------- */
SELECT
    COALESCE(REVISOR, '(sin revisor)')                             AS REVISOR,
    COUNT(*)                                                       AS CICLOS,
    ROUND(AVG(DIAS_EN_COLA), 2)                                    AS PROM_DIAS_COLA,
    ROUND(AVG(DIAS_TRABAJO_EFECTIVO), 2)                           AS PROM_DIAS_TRABAJO,
    ROUND(AVG(DIAS_CICLO), 2)                                      AS PROM_DIAS_TOTAL
FROM V_ACRED_CICLO
WHERE FECHA_DESENLACE IS NOT NULL
GROUP BY REVISOR
ORDER BY PROM_DIAS_TOTAL DESC;
