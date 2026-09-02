/* =============================================================================
   BLOQUE 04 · RETRABAJO Y CAUSAS DE RECHAZO
   -----------------------------------------------------------------------------
   El tiempo de acreditación casi nunca es un problema de velocidad de revisión:
   es un problema de cuántas veces hay que revisar lo mismo. Este bloque
   identifica QUÉ documento y QUÉ motivo generan las vueltas.
   ============================================================================= */

SET SESSION group_concat_max_len = 10000000;


/* -----------------------------------------------------------------------------
   04.1 · IMPACTO DEL RETRABAJO EN EL TIEMPO  → GRÁFICO: barras
   La lectura esperada: cada rechazo adicional suma X días al lead time.
   Este es el número que justifica invertir en capacitar a las EECC.
----------------------------------------------------------------------------- */
SELECT
    LEAST(COALESCE(N_RECHAZOS, 0), 5)                              AS RECHAZOS,
    COUNT(*)                                                       AS CASOS,
    ROUND(100 * COUNT(*) / (SELECT COUNT(*) FROM V_ACRED_CASO), 1) AS PCT_CASOS,
    ROUND(AVG(DIAS_TOTAL), 2)                                      AS PROMEDIO_DIAS,
    CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(
        GROUP_CONCAT(DIAS_TOTAL ORDER BY DIAS_TOTAL SEPARATOR ','),
        ',', GREATEST(1, CEILING(COUNT(DIAS_TOTAL) * 0.50))), ',', -1)
        AS DECIMAL(10,2))                                          AS MEDIANA_DIAS,
    ROUND(100 * SUM(ESTADO_CASO = 'CERRADO') / COUNT(*), 1)        AS PCT_CIERRE
FROM V_ACRED_CASO
GROUP BY RECHAZOS
ORDER BY RECHAZOS;


/* -----------------------------------------------------------------------------
   04.2 · TOP DOCUMENTOS QUE BLOQUEAN  → GRÁFICO: barras horizontales (Pareto)
   Usa ID_DOCUMENTO_BLOQUEO del log de estados. Normalmente el 80% de las
   vueltas se concentra en 4-6 documentos.
----------------------------------------------------------------------------- */
SELECT
    COALESCE(doc.NOMBRE, CONCAT('ID ', est.ID_DOCUMENTO_BLOQUEO))  AS DOCUMENTO_BLOQUEANTE,
    cat.NOMBRE                                                     AS CATEGORIA,
    doc.REQUERIDO,
    COUNT(*)                                                       AS VECES_BLOQUEO,
    COUNT(DISTINCT est.ID_ASIGNACION)                              AS TRABAJADORES_AFECTADOS,
    ROUND(100 * COUNT(*) / (
        SELECT COUNT(*) FROM DB_LEGAV_STATUS_ACREDITACION_PERSONA s
        JOIN V_ACRED_ESTADO_CLASIF c ON c.ID_ESTADO_ACREDITACION = s.ID_ESTADO_ACREDITACION
        WHERE c.GRUPO_ESTADO = 'RECHAZADO' AND s.ID_DOCUMENTO_BLOQUEO IS NOT NULL), 1)
                                                                   AS PCT_DEL_TOTAL,
    MIN(est.FECHA_REGISTRO)                                        AS DESDE,
    MAX(est.FECHA_REGISTRO)                                        AS HASTA
FROM DB_LEGAV_STATUS_ACREDITACION_PERSONA est
JOIN V_ACRED_ESTADO_CLASIF cls ON cls.ID_ESTADO_ACREDITACION = est.ID_ESTADO_ACREDITACION
LEFT JOIN DB_DOCUMENTO_ESTANDAR_ACREDITACION doc ON doc.ID_DOCUMENTO   = est.ID_DOCUMENTO_BLOQUEO
LEFT JOIN DB_LEGAV_CAT_ESTANDAR_DOCUMENTAL   cat ON cat.ID_CAT_ESTANDAR = doc.ID_CAT_ESTANDAR
WHERE cls.GRUPO_ESTADO = 'RECHAZADO'
  AND est.ID_DOCUMENTO_BLOQUEO IS NOT NULL
GROUP BY est.ID_DOCUMENTO_BLOQUEO, DOCUMENTO_BLOQUEANTE, cat.NOMBRE, doc.REQUERIDO
ORDER BY VECES_BLOQUEO DESC
LIMIT 25;


/* -----------------------------------------------------------------------------
   04.3 · MOTIVOS DE RECHAZO EN TEXTO LIBRE  → nube de causas / tabla
   Agrupa observaciones normalizadas. Si sale muy disperso, es señal de que
   el campo OBSERVACION debería ser un catálogo cerrado (hallazgo del informe).
----------------------------------------------------------------------------- */
SELECT
    UPPER(TRIM(SUBSTRING(est.OBSERVACION, 1, 80)))                 AS MOTIVO,
    COUNT(*)                                                       AS VECES,
    COUNT(DISTINCT est.ID_ASIGNACION)                              AS TRABAJADORES,
    COUNT(DISTINCT est.ID_USU_LEGAV)                               AS REVISORES_QUE_LO_USAN
FROM DB_LEGAV_STATUS_ACREDITACION_PERSONA est
JOIN V_ACRED_ESTADO_CLASIF cls ON cls.ID_ESTADO_ACREDITACION = est.ID_ESTADO_ACREDITACION
WHERE cls.GRUPO_ESTADO = 'RECHAZADO'
  AND est.OBSERVACION IS NOT NULL
  AND TRIM(est.OBSERVACION) <> ''
GROUP BY MOTIVO
ORDER BY VECES DESC
LIMIT 40;


/* -----------------------------------------------------------------------------
   04.4 · EMPRESAS CON MÁS RETRABAJO  → tabla de gestión con EECC
----------------------------------------------------------------------------- */
SELECT
    EMPRESA,
    COUNT(*)                                                       AS CASOS,
    SUM(N_SOLICITUDES)                                             AS ENVIOS_TOTALES,
    ROUND(AVG(N_SOLICITUDES), 2)                                   AS ENVIOS_POR_CASO,
    SUM(COALESCE(N_RECHAZOS, 0))                                   AS RECHAZOS_TOTALES,
    ROUND(100 * SUM(COALESCE(N_RECHAZOS,0) > 0) / COUNT(*), 1)     AS PCT_CASOS_CON_RECHAZO,
    /* envíos "desperdiciados": todo lo que va más allá del primero */
    SUM(N_SOLICITUDES) - COUNT(*)                                  AS ENVIOS_EVITABLES,
    ROUND(AVG(DIAS_TOTAL), 2)                                      AS PROMEDIO_DIAS,
    ROUND(AVG(DIAS_EN_CONTRATISTA), 2)                             AS DIAS_CORRIGIENDO
FROM V_ACRED_CASO
GROUP BY EMPRESA
HAVING COUNT(*) >= 5
ORDER BY ENVIOS_POR_CASO DESC, RECHAZOS_TOTALES DESC;


/* -----------------------------------------------------------------------------
   04.5 · TASA DE APROBACIÓN AL PRIMER INTENTO (FPY) POR MES Y EMPRESA
   First Pass Yield: el indicador de calidad más honesto del proceso.
----------------------------------------------------------------------------- */
SELECT
    MES_SOLICITUD                                                  AS MES,
    COUNT(*)                                                       AS CASOS,
    SUM(N_SOLICITUDES = 1 AND ESTADO_CASO = 'CERRADO')             AS APROBADOS_AL_PRIMER_INTENTO,
    ROUND(100 * SUM(N_SOLICITUDES = 1 AND ESTADO_CASO = 'CERRADO')
              / COUNT(*), 1)                                       AS FPY_PCT
FROM V_ACRED_CASO
WHERE MES_SOLICITUD IS NOT NULL
GROUP BY MES_SOLICITUD
ORDER BY MES_SOLICITUD;


/* -----------------------------------------------------------------------------
   04.6 · DOCUMENTOS: TIEMPO DE CARGA vs TIEMPO DE REVISIÓN
   Detecta documentos que se cargan pero nadie revisa (VISTO nulo) — una fuente
   silenciosa de días perdidos.
----------------------------------------------------------------------------- */
SELECT
    de.NOMBRE                                                      AS DOCUMENTO,
    cat.NOMBRE                                                     AS CATEGORIA,
    de.REQUERIDO,
    COUNT(*)                                                       AS CARGAS,
    SUM(dp.VISTO IS NULL)                                          AS SIN_REVISAR,
    ROUND(100 * SUM(dp.VISTO IS NULL) / COUNT(*), 1)               AS PCT_SIN_REVISAR,
    ROUND(AVG(TIMESTAMPDIFF(HOUR, dp.FECHA_REGISTRO, dp.VISTO)/24), 2)
                                                                   AS DIAS_PROM_REVISION,
    SUM(dp.FECHA_TERMINO IS NOT NULL AND dp.FECHA_TERMINO < CURDATE())
                                                                   AS VENCIDOS_HOY
FROM DB_DOCUMENTO_PERSONAL dp
LEFT JOIN DB_DOCUMENTO_ESTANDAR_ACREDITACION de  ON de.ID_DOCUMENTO    = dp.ID_DOCUMENTO
LEFT JOIN DB_LEGAV_CAT_ESTANDAR_DOCUMENTAL  cat ON cat.ID_CAT_ESTANDAR = de.ID_CAT_ESTANDAR
GROUP BY dp.ID_DOCUMENTO, de.NOMBRE, cat.NOMBRE, de.REQUERIDO
ORDER BY CARGAS DESC
LIMIT 40;
