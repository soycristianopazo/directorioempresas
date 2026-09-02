/* =============================================================================
   BLOQUE 02 · DATASETS PARA EXPORTAR A CSV
   -----------------------------------------------------------------------------
   Estos son los 3 archivos que necesito para armar el informe. Con el primero
   solo ya se puede construir casi todo; los otros dos agregan el detalle de
   retrabajo y de causas de rechazo.

   En phpMyAdmin: ejecutar → "Exportar" → CSV → separador coma → incluir
   nombres de columna en la primera fila → codificación UTF-8.

   Si la BD es grande, filtrar por periodo descomentando la línea de fecha.
   ============================================================================= */

SET SESSION group_concat_max_len = 10000000;


/* =============================================================================
   CSV 1 · acred_casos.csv     ← EL PRINCIPAL. Una fila por trabajador-contrato.
   Contiene el lead time punta a punta, el retrabajo y el reloj partido.
   ============================================================================= */
SELECT
    ID_ASIGNACION,
    RUT_TRABAJADOR,
    TRABAJADOR,
    CARGO,
    EMPRESA,
    ID_EMPRESA,
    MANDANTE,
    GERENCIA,
    NUMERO_ACUERDO,
    CONTRATO,
    FECHA_ASIGNACION,
    F_PRIMERA_SOLICITUD,
    F_ULTIMA_SOLICITUD,
    F_APROBACION,
    ESTADO_CASO,
    ESTADO_ACTUAL,
    GRUPO_ACTUAL,
    N_SOLICITUDES,
    N_RECHAZOS,
    DIAS_PREPARACION,
    DIAS_TOTAL,
    DIAS_ULTIMO_ENVIO,
    DIAS_EN_MANDANTE,
    DIAS_EN_CONTRATISTA,
    DIAS_ANTIGUEDAD,
    MES_SOLICITUD,
    MES_APROBACION,
    /* días hábiles aprox. (lun-vie, SIN feriados chilenos) */
    CASE WHEN F_APROBACION IS NULL THEN NULL ELSE
        5 * (DATEDIFF(F_APROBACION, F_PRIMERA_SOLICITUD) DIV 7)
        + CAST(MID('0123444401233334012222340111123400001234000123440',
                   7 * WEEKDAY(F_PRIMERA_SOLICITUD) + WEEKDAY(F_APROBACION) + 1, 1)
               AS UNSIGNED)
    END AS DIAS_HABILES_TOTAL,
    /* tramo de SLA para el gráfico de distribución */
    CASE
        WHEN DIAS_TOTAL IS NULL      THEN '99 · sin aprobar'
        WHEN DIAS_TOTAL <  1         THEN '01 · mismo día'
        WHEN DIAS_TOTAL <  2         THEN '02 · 1 día'
        WHEN DIAS_TOTAL <  4         THEN '03 · 2-3 días'
        WHEN DIAS_TOTAL <  8         THEN '04 · 4-7 días'
        WHEN DIAS_TOTAL <  15        THEN '05 · 8-14 días'
        WHEN DIAS_TOTAL <  31        THEN '06 · 15-30 días'
        ELSE                              '07 · más de 30 días'
    END AS TRAMO_SLA
FROM V_ACRED_CASO
-- WHERE F_PRIMERA_SOLICITUD >= '2025-01-01'
ORDER BY F_PRIMERA_SOLICITUD;


/* =============================================================================
   CSV 2 · acred_ciclos.csv    ← Una fila por vuelta de revisión.
   Sirve para medir el SLA del acreditador y ver dónde se rompe el flujo.
   ============================================================================= */
SELECT
    ID_SOLICITUD,
    ID_ASIGNACION,
    NRO_CICLO,
    RUT_TRABAJADOR,
    TRABAJADOR,
    EMPRESA,
    MANDANTE,
    GERENCIA,
    NUMERO_ACUERDO,
    FECHA_SOLICITUD,
    FECHA_REVISION,
    FECHA_DESENLACE,
    RESULTADO_CICLO,
    ESTADO_DESENLACE,
    REVISOR,
    ID_REVISOR,
    DOCUMENTO_BLOQUEO,
    OBS_DESENLACE,
    HORAS_CICLO,
    DIAS_CICLO,
    HORAS_HASTA_REVISION,
    DIA_SOLICITUD,
    MES_SOLICITUD,
    DIA_SEMANA_SOLICITUD,
    HORA_SOLICITUD
FROM V_ACRED_CICLO
-- WHERE FECHA_SOLICITUD >= '2025-01-01'
ORDER BY ID_ASIGNACION, NRO_CICLO;


/* =============================================================================
   CSV 3 · acred_documentos.csv  ← Documentos cargados por trabajador.
   Permite cruzar tiempo de acreditación contra carga documental y vencimientos.
   ============================================================================= */
SELECT
    dp.ID_ARCHIVO,
    dp.ID_PERSONA,
    per.RUT                                        AS RUT_TRABAJADOR,
    COALESCE(emp.NOMBRE_FANTASIA, emp.NOMBRE)      AS EMPRESA,
    de.ID_DOCUMENTO,
    de.NOMBRE                                      AS DOCUMENTO,
    cat.NOMBRE                                     AS CATEGORIA_DOCUMENTAL,
    de.REQUERIDO,
    de.TRANSVERSAL,
    de.CONTROL_ACCESO,
    de.INDEFINIDO,
    dp.FECHA_REGISTRO                              AS FECHA_CARGA,
    dp.VISTO                                       AS FECHA_REVISADO,
    dp.FECHA_INICIO                                AS VIGENCIA_DESDE,
    dp.FECHA_TERMINO                               AS VIGENCIA_HASTA,
    ROUND(TIMESTAMPDIFF(HOUR, dp.FECHA_REGISTRO, dp.VISTO)/24, 2)
                                                   AS DIAS_HASTA_REVISION_DOC,
    CASE
        WHEN dp.FECHA_TERMINO IS NULL              THEN 'SIN_VENCIMIENTO'
        WHEN dp.FECHA_TERMINO <  CURDATE()         THEN 'VENCIDO'
        WHEN dp.FECHA_TERMINO <= CURDATE() + INTERVAL 30 DAY THEN 'POR_VENCER_30D'
        ELSE 'VIGENTE'
    END                                            AS ESTADO_VIGENCIA,
    CASE WHEN dp.VISTO IS NULL THEN 'PENDIENTE_REVISION' ELSE 'REVISADO' END
                                                   AS ESTADO_REVISION
FROM DB_DOCUMENTO_PERSONAL dp
LEFT JOIN DB_LEGAV_PERSONAL_ACREDITACION      per ON per.ID_PERSONA   = dp.ID_PERSONA
LEFT JOIN DB_LEGAV_EMPRESA                    emp ON emp.ID_EMPRESA   = per.ID_EMPRESA
LEFT JOIN DB_DOCUMENTO_ESTANDAR_ACREDITACION  de  ON de.ID_DOCUMENTO  = dp.ID_DOCUMENTO
LEFT JOIN DB_LEGAV_CAT_ESTANDAR_DOCUMENTAL    cat ON cat.ID_CAT_ESTANDAR = de.ID_CAT_ESTANDAR
-- WHERE dp.FECHA_REGISTRO >= '2025-01-01'
ORDER BY dp.FECHA_REGISTRO;
