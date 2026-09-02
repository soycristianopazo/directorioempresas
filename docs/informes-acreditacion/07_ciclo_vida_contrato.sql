/* =============================================================================
   CICLO DE VIDA COMPLETO — desde la creación del contrato
   BD legavcl_caitan · MySQL 5.7 · autocontenidas, no requieren crear vistas
   IDs de estado confirmados: 1 En Revisión · 2 Acreditado · 3,4,5 rechazos

   La cadena que se mide:
     CONTRATO_EMP.FECHA_REGISTRO   se crea el contrato comercial
        → ASIG_PERSONAL_ACUERDO    se asigna al trabajador (ID_ASIGNACION)
        → SOLICITUD_ACREDITACION   se pide la acreditación
        → STATUS_..._PERSONA       cambios de estado hasta «Acreditado»

   Ejecutar cada una por separado y exportar a CSV (UTF-8, coma, con cabecera).
   ============================================================================= */


/* =============================================================================
   CSV A · contratos.csv — una fila por contrato comercial
   Responde: ¿cuánto tarda un contrato desde que se crea hasta tener su primer
   trabajador acreditado? ¿cuántos contratos nunca llegaron a tener gente?
   ============================================================================= */
SELECT
    con.ID_REG_CONTRATO,
    con.NUMERO_ACUERDO,
    con.DESCRIPCION                                   AS CONTRATO,
    con.SUB_CONTRATO,
    con.ESTADO                                        AS ESTADO_CONTRATO,
    emp.RUT                                           AS RUT_EMPRESA,
    COALESCE(emp.NOMBRE_FANTASIA, emp.NOMBRE)         AS EMPRESA,
    man.NOMBRE_FAENA                                  AS MANDANTE,
    ger.DESCRIPCION                                   AS GERENCIA,
    con.FECHA_REGISTRO                                AS F_CREACION_CONTRATO,
    con.FECHA_INICIO                                  AS F_INICIO_CONTRATO,
    con.FECHA_TERMINO                                 AS F_TERMINO_CONTRATO,
    con.LIMITE_CONTINGENTE,
    COALESCE(a.N_TRABAJADORES, 0)                     AS N_TRABAJADORES,
    a.F_PRIMERA_ASIGNACION,
    a.F_ULTIMA_ASIGNACION,
    COALESCE(so.N_SOLICITUDES, 0)                     AS N_SOLICITUDES,
    so.F_PRIMERA_SOLICITUD,
    COALESCE(ap.N_ACREDITADOS, 0)                     AS N_ACREDITADOS,
    ap.F_PRIMERA_ACREDITACION,
    ap.F_ULTIMA_ACREDITACION,
    COALESCE(rz.N_RECHAZOS, 0)                        AS N_RECHAZOS,
    /* ---- hitos de arranque del contrato, en días ---- */
    ROUND(TIMESTAMPDIFF(HOUR, con.FECHA_REGISTRO, a.F_PRIMERA_ASIGNACION)/24, 2)
                                                      AS DIAS_HASTA_1A_ASIGNACION,
    ROUND(TIMESTAMPDIFF(HOUR, con.FECHA_REGISTRO, so.F_PRIMERA_SOLICITUD)/24, 2)
                                                      AS DIAS_HASTA_1A_SOLICITUD,
    ROUND(TIMESTAMPDIFF(HOUR, con.FECHA_REGISTRO, ap.F_PRIMERA_ACREDITACION)/24, 2)
                                                      AS DIAS_HASTA_1ER_ACREDITADO,
    ROUND(TIMESTAMPDIFF(HOUR, con.FECHA_INICIO, ap.F_PRIMERA_ACREDITACION)/24, 2)
                                                      AS DIAS_INICIO_A_1ER_ACREDITADO,
    /* cuántos quedaron acreditados dentro de los primeros 30 / 60 / 90 días del contrato */
    COALESCE(v.ACRED_30D, 0)                          AS ACRED_30D,
    COALESCE(v.ACRED_60D, 0)                          AS ACRED_60D,
    COALESCE(v.ACRED_90D, 0)                          AS ACRED_90D,
    DATE_FORMAT(con.FECHA_REGISTRO, '%Y-%m')          AS MES_CREACION,
    YEAR(con.FECHA_REGISTRO)                          AS ANIO_CREACION
FROM DB_LEGAV_CONTRATO_EMP con
LEFT JOIN DB_LEGAV_EMPRESA              emp ON emp.ID_EMPRESA  = con.ID_EMPRESA
LEFT JOIN DB_LEGAV_MANDANTE             man ON man.ID_MANDANTE = con.ID_MANDANTE
LEFT JOIN DB_LEGAV_MAN_GERENCIA_DETALLE gd  ON gd.ID_DETALLE_GERENCIA = con.ID_DETALLE_GERENCIA
LEFT JOIN DB_LEGAV_MANDANTE_GERENCIA    ger ON ger.ID_GERENCIA  = gd.ID_GERENCIA
LEFT JOIN (
    SELECT ID_REG_ACUERDOS AS C, COUNT(*) AS N_TRABAJADORES,
           MIN(FECHA_REGISTRO) AS F_PRIMERA_ASIGNACION,
           MAX(FECHA_REGISTRO) AS F_ULTIMA_ASIGNACION
    FROM DB_LEGAV_ASIG_PERSONAL_ACUERDO GROUP BY ID_REG_ACUERDOS
) a ON a.C = con.ID_REG_CONTRATO
LEFT JOIN (
    SELECT g.ID_REG_ACUERDOS AS C, COUNT(*) AS N_SOLICITUDES,
           MIN(s.FECHA_REGISTRO) AS F_PRIMERA_SOLICITUD
    FROM DB_LEGAV_SOLICITUD_ACREDITACION s
    JOIN DB_LEGAV_ASIG_PERSONAL_ACUERDO g ON g.ID_ASIGNACION = s.ID_ASIGNACION
    WHERE s.FECHA_REGISTRO IS NOT NULL
    GROUP BY g.ID_REG_ACUERDOS
) so ON so.C = con.ID_REG_CONTRATO
LEFT JOIN (
    SELECT g.ID_REG_ACUERDOS AS C, COUNT(DISTINCT p.ID_ASIGNACION) AS N_ACREDITADOS,
           MIN(p.F) AS F_PRIMERA_ACREDITACION, MAX(p.F) AS F_ULTIMA_ACREDITACION
    FROM (
        SELECT ID_ASIGNACION, MIN(FECHA_REGISTRO) AS F
        FROM DB_LEGAV_STATUS_ACREDITACION_PERSONA
        WHERE ID_ESTADO_ACREDITACION = 2 GROUP BY ID_ASIGNACION
    ) p
    JOIN DB_LEGAV_ASIG_PERSONAL_ACUERDO g ON g.ID_ASIGNACION = p.ID_ASIGNACION
    GROUP BY g.ID_REG_ACUERDOS
) ap ON ap.C = con.ID_REG_CONTRATO
LEFT JOIN (
    SELECT g.ID_REG_ACUERDOS AS C, COUNT(*) AS N_RECHAZOS
    FROM DB_LEGAV_STATUS_ACREDITACION_PERSONA e
    JOIN DB_LEGAV_ASIG_PERSONAL_ACUERDO g ON g.ID_ASIGNACION = e.ID_ASIGNACION
    WHERE e.ID_ESTADO_ACREDITACION IN (3,4,5)
    GROUP BY g.ID_REG_ACUERDOS
) rz ON rz.C = con.ID_REG_CONTRATO
LEFT JOIN (
    SELECT g.ID_REG_ACUERDOS AS C,
      SUM(p.F <= c2.FECHA_REGISTRO + INTERVAL 30 DAY) AS ACRED_30D,
      SUM(p.F <= c2.FECHA_REGISTRO + INTERVAL 60 DAY) AS ACRED_60D,
      SUM(p.F <= c2.FECHA_REGISTRO + INTERVAL 90 DAY) AS ACRED_90D
    FROM (
        SELECT ID_ASIGNACION, MIN(FECHA_REGISTRO) AS F
        FROM DB_LEGAV_STATUS_ACREDITACION_PERSONA
        WHERE ID_ESTADO_ACREDITACION = 2 GROUP BY ID_ASIGNACION
    ) p
    JOIN DB_LEGAV_ASIG_PERSONAL_ACUERDO g ON g.ID_ASIGNACION = p.ID_ASIGNACION
    JOIN DB_LEGAV_CONTRATO_EMP c2 ON c2.ID_REG_CONTRATO = g.ID_REG_ACUERDOS
    GROUP BY g.ID_REG_ACUERDOS
) v ON v.C = con.ID_REG_CONTRATO
ORDER BY con.FECHA_REGISTRO;


/* =============================================================================
   CSV B · casos2.csv — una fila por trabajador, con la línea de tiempo completa
   Reemplaza al anterior acred_casos.csv: agrega el contrato y sus fechas.
   ============================================================================= */
SELECT
    asg.ID_ASIGNACION,
    con.ID_REG_CONTRATO,
    con.NUMERO_ACUERDO,
    con.ESTADO                                       AS ESTADO_CONTRATO,
    per.RUT                                          AS RUT_TRABAJADOR,
    TRIM(CONCAT_WS(' ', per.NOMBRE, per.APELLIDO))   AS TRABAJADOR,
    per.CARGO,
    COALESCE(emp.NOMBRE_FANTASIA, emp.NOMBRE)        AS EMPRESA,
    man.NOMBRE_FAENA                                 AS MANDANTE,
    ger.DESCRIPCION                                  AS GERENCIA,

    /* ---- los cinco hitos de la línea de tiempo ---- */
    con.FECHA_REGISTRO                               AS F_CREACION_CONTRATO,
    con.FECHA_INICIO                                 AS F_INICIO_CONTRATO,
    asg.FECHA_REGISTRO                               AS F_ASIGNACION,
    sol.F_PRIMERA_SOLICITUD,
    sol.F_ULTIMA_SOLICITUD,
    est.F_PRIMER_ESTADO,
    ap.F_APROBACION,
    ult.ESTADO_ACTUAL,
    ult.F_ULTIMO_ESTADO,

    sol.N_SOLICITUDES,
    COALESCE(rz.N_RECHAZOS, 0)                       AS N_RECHAZOS,
    CASE WHEN ap.F_APROBACION IS NULL THEN 'ABIERTO' ELSE 'CERRADO' END AS ESTADO_CASO,

    /* ---- tramos, en días ---- */
    ROUND(TIMESTAMPDIFF(HOUR, con.FECHA_REGISTRO, asg.FECHA_REGISTRO)/24, 2)
                                                     AS D_CONTRATO_A_ASIGNACION,
    ROUND(TIMESTAMPDIFF(HOUR, asg.FECHA_REGISTRO, sol.F_PRIMERA_SOLICITUD)/24, 2)
                                                     AS D_ASIGNACION_A_SOLICITUD,
    ROUND(TIMESTAMPDIFF(HOUR, sol.F_PRIMERA_SOLICITUD, ap.F_APROBACION)/24, 2)
                                                     AS D_SOLICITUD_A_APROBACION,
    ROUND(TIMESTAMPDIFF(HOUR, con.FECHA_REGISTRO, ap.F_APROBACION)/24, 2)
                                                     AS D_CONTRATO_A_APROBACION,
    ROUND(TIMESTAMPDIFF(HOUR, asg.FECHA_REGISTRO, ap.F_APROBACION)/24, 2)
                                                     AS D_ASIGNACION_A_APROBACION,
    ROUND(TIMESTAMPDIFF(HOUR, sol.F_ULTIMA_SOLICITUD, ap.F_APROBACION)/24, 2)
                                                     AS D_ULTIMO_ENVIO,
    ROUND(cic.HORAS_MANDANTE/24, 2)                  AS D_EN_REVISION_SUMA,
    ROUND(TIMESTAMPDIFF(HOUR, sol.F_PRIMERA_SOLICITUD, NOW())/24, 0)
                                                     AS D_ANTIGUEDAD,
    DATE_FORMAT(con.FECHA_REGISTRO, '%Y-%m')         AS MES_CONTRATO,
    DATE_FORMAT(sol.F_PRIMERA_SOLICITUD, '%Y-%m')    AS MES_SOLICITUD,
    DATE_FORMAT(ap.F_APROBACION, '%Y-%m')            AS MES_APROBACION
FROM DB_LEGAV_ASIG_PERSONAL_ACUERDO asg
LEFT JOIN DB_LEGAV_PERSONAL_ACREDITACION per ON per.ID_PERSONA      = asg.ID_PERSONA
LEFT JOIN DB_LEGAV_CONTRATO_EMP          con ON con.ID_REG_CONTRATO = asg.ID_REG_ACUERDOS
LEFT JOIN DB_LEGAV_EMPRESA               emp ON emp.ID_EMPRESA      = COALESCE(con.ID_EMPRESA, per.ID_EMPRESA)
LEFT JOIN DB_LEGAV_MANDANTE              man ON man.ID_MANDANTE     = con.ID_MANDANTE
LEFT JOIN DB_LEGAV_MAN_GERENCIA_DETALLE  gd  ON gd.ID_DETALLE_GERENCIA = con.ID_DETALLE_GERENCIA
LEFT JOIN DB_LEGAV_MANDANTE_GERENCIA     ger ON ger.ID_GERENCIA     = gd.ID_GERENCIA
LEFT JOIN (
    SELECT ID_ASIGNACION, MIN(FECHA_REGISTRO) AS F_PRIMERA_SOLICITUD,
           MAX(FECHA_REGISTRO) AS F_ULTIMA_SOLICITUD, COUNT(*) AS N_SOLICITUDES
    FROM DB_LEGAV_SOLICITUD_ACREDITACION
    WHERE FECHA_REGISTRO IS NOT NULL GROUP BY ID_ASIGNACION
) sol ON sol.ID_ASIGNACION = asg.ID_ASIGNACION
LEFT JOIN (
    SELECT ID_ASIGNACION, MIN(FECHA_REGISTRO) AS F_PRIMER_ESTADO
    FROM DB_LEGAV_STATUS_ACREDITACION_PERSONA GROUP BY ID_ASIGNACION
) est ON est.ID_ASIGNACION = asg.ID_ASIGNACION
LEFT JOIN (
    SELECT ID_ASIGNACION, MIN(FECHA_REGISTRO) AS F_APROBACION
    FROM DB_LEGAV_STATUS_ACREDITACION_PERSONA
    WHERE ID_ESTADO_ACREDITACION = 2 GROUP BY ID_ASIGNACION
) ap ON ap.ID_ASIGNACION = asg.ID_ASIGNACION
LEFT JOIN (
    SELECT ID_ASIGNACION, COUNT(*) AS N_RECHAZOS
    FROM DB_LEGAV_STATUS_ACREDITACION_PERSONA
    WHERE ID_ESTADO_ACREDITACION IN (3,4,5) GROUP BY ID_ASIGNACION
) rz ON rz.ID_ASIGNACION = asg.ID_ASIGNACION
LEFT JOIN (
    SELECT s.ID_ASIGNACION,
           SUM(TIMESTAMPDIFF(HOUR, s.FECHA_REGISTRO, e.FECHA_REGISTRO)) AS HORAS_MANDANTE
    FROM DB_LEGAV_SOLICITUD_ACREDITACION s
    JOIN DB_LEGAV_STATUS_ACREDITACION_PERSONA e ON e.ID_ESTATUS = (
        SELECT MIN(e2.ID_ESTATUS) FROM DB_LEGAV_STATUS_ACREDITACION_PERSONA e2
        WHERE e2.ID_ASIGNACION = s.ID_ASIGNACION
          AND e2.FECHA_REGISTRO >= s.FECHA_REGISTRO
          AND e2.ID_ESTADO_ACREDITACION IN (2,3,4,5))
    WHERE s.FECHA_REGISTRO IS NOT NULL GROUP BY s.ID_ASIGNACION
) cic ON cic.ID_ASIGNACION = asg.ID_ASIGNACION
LEFT JOIN (
    SELECT e.ID_ASIGNACION, c.DESCRIPCION AS ESTADO_ACTUAL, e.FECHA_REGISTRO AS F_ULTIMO_ESTADO
    FROM DB_LEGAV_STATUS_ACREDITACION_PERSONA e
    JOIN DB_LEGAV_ESTATUS_ACREDITACION c ON c.ID_ESTADO_ACREDITACION = e.ID_ESTADO_ACREDITACION
    JOIN (SELECT ID_ASIGNACION, MAX(ID_ESTATUS) AS ID_ESTATUS
          FROM DB_LEGAV_STATUS_ACREDITACION_PERSONA GROUP BY ID_ASIGNACION) m
      ON m.ID_ESTATUS = e.ID_ESTATUS
) ult ON ult.ID_ASIGNACION = asg.ID_ASIGNACION
ORDER BY con.FECHA_REGISTRO, asg.FECHA_REGISTRO;


/* =============================================================================
   CSV C · estados.csv — una fila por cambio de estado (log completo)
   Permite analizar transiciones, tiempo en cada estado y quién las registra.
   ============================================================================= */
SELECT
    e.ID_ESTATUS,
    e.ID_ASIGNACION,
    g.ID_REG_ACUERDOS                                AS ID_REG_CONTRATO,
    con.NUMERO_ACUERDO,
    per.RUT                                          AS RUT_TRABAJADOR,
    COALESCE(emp.NOMBRE_FANTASIA, emp.NOMBRE)        AS EMPRESA,
    e.ID_ESTADO_ACREDITACION,
    cat.DESCRIPCION                                  AS ESTADO,
    e.FECHA_REGISTRO                                 AS F_ESTADO,
    TRIM(CONCAT_WS(' ', adm.NOMBRE, adm.APELLIDO))   AS REGISTRADO_POR,
    e.ID_DOCUMENTO_BLOQUEO,
    doc.NOMBRE                                       AS DOCUMENTO_BLOQUEO,
    e.OBSERVACION,
    /* orden del cambio dentro del trabajador y horas desde el estado anterior */
    (SELECT COUNT(*) FROM DB_LEGAV_STATUS_ACREDITACION_PERSONA x
      WHERE x.ID_ASIGNACION = e.ID_ASIGNACION AND x.ID_ESTATUS <= e.ID_ESTATUS) AS NRO_CAMBIO,
    (SELECT MAX(y.FECHA_REGISTRO) FROM DB_LEGAV_STATUS_ACREDITACION_PERSONA y
      WHERE y.ID_ASIGNACION = e.ID_ASIGNACION AND y.ID_ESTATUS < e.ID_ESTATUS) AS F_ESTADO_ANTERIOR,
    DATE_FORMAT(e.FECHA_REGISTRO, '%Y-%m')           AS MES_ESTADO
FROM DB_LEGAV_STATUS_ACREDITACION_PERSONA e
LEFT JOIN DB_LEGAV_ESTATUS_ACREDITACION      cat ON cat.ID_ESTADO_ACREDITACION = e.ID_ESTADO_ACREDITACION
LEFT JOIN DB_LEGAV_ASIG_PERSONAL_ACUERDO     g   ON g.ID_ASIGNACION  = e.ID_ASIGNACION
LEFT JOIN DB_LEGAV_PERSONAL_ACREDITACION     per ON per.ID_PERSONA   = g.ID_PERSONA
LEFT JOIN DB_LEGAV_CONTRATO_EMP              con ON con.ID_REG_CONTRATO = g.ID_REG_ACUERDOS
LEFT JOIN DB_LEGAV_EMPRESA                   emp ON emp.ID_EMPRESA   = con.ID_EMPRESA
LEFT JOIN DB_LEGAV_ADMINISTRATIVOS           adm ON adm.ID_USU_LEGAV = e.ID_USU_LEGAV
LEFT JOIN DB_DOCUMENTO_ESTANDAR_ACREDITACION doc ON doc.ID_DOCUMENTO = e.ID_DOCUMENTO_BLOQUEO
ORDER BY e.ID_ASIGNACION, e.ID_ESTATUS;
