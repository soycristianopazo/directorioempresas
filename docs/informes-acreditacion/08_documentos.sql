-- =============================================================================
-- CSV D · documentos.csv — una fila por documento cargado
-- BD legavcl_caitan · MySQL 5.7
--
-- Permite separar el tiempo de la empresa contratista del tiempo del acreditador:
--   F_CARGA    = cuándo la empresa subió el documento
--   F_REVISADO = cuándo el acreditador lo revisó (columna VISTO)
--
-- Ejecutar tal cual en la pestaña SQL y exportar a CSV (UTF-8, coma, con cabecera).
-- =============================================================================
SELECT
    dp.ID_ARCHIVO,
    dp.ID_PERSONA,
    per.RUT                                          AS RUT_TRABAJADOR,
    COALESCE(emp.NOMBRE_FANTASIA, emp.NOMBRE)        AS EMPRESA,
    de.ID_DOCUMENTO,
    de.NOMBRE                                        AS DOCUMENTO,
    cat.NOMBRE                                       AS CATEGORIA,
    de.REQUERIDO,
    dp.FECHA_REGISTRO                                AS F_CARGA,
    dp.VISTO                                         AS F_REVISADO,
    dp.FECHA_INICIO                                  AS VIGENCIA_DESDE,
    dp.FECHA_TERMINO                                 AS VIGENCIA_HASTA,
    dp.ID_USUARIO                                    AS CARGADO_POR_EECC,
    dp.ID_USU_LEGAV                                  AS REVISADO_POR,
    ROUND(TIMESTAMPDIFF(HOUR, dp.FECHA_REGISTRO, dp.VISTO)/24, 2) AS DIAS_HASTA_REVISION,
    DATE_FORMAT(dp.FECHA_REGISTRO, '%Y-%m')          AS MES_CARGA
FROM DB_DOCUMENTO_PERSONAL dp
LEFT JOIN DB_LEGAV_PERSONAL_ACREDITACION     per ON per.ID_PERSONA   = dp.ID_PERSONA
LEFT JOIN DB_LEGAV_EMPRESA                   emp ON emp.ID_EMPRESA   = per.ID_EMPRESA
LEFT JOIN DB_DOCUMENTO_ESTANDAR_ACREDITACION de  ON de.ID_DOCUMENTO  = dp.ID_DOCUMENTO
LEFT JOIN DB_LEGAV_CAT_ESTANDAR_DOCUMENTAL   cat ON cat.ID_CAT_ESTANDAR = de.ID_CAT_ESTANDAR
ORDER BY dp.ID_PERSONA, dp.FECHA_REGISTRO;
