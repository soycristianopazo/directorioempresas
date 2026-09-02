/* =============================================================================
   BLOQUE 01 · VISTAS BASE (capa semántica)
   -----------------------------------------------------------------------------
   Son 3 objetos de SOLO LECTURA. No modifican ni una fila de datos.
   Todo el resto del pack se apoya en ellas: si algo hay que corregir, se
   corrige aquí una vez y no en 20 queries.

   Si no tienes permiso CREATE VIEW, en cada query posterior reemplaza el nombre
   de la vista por su SELECT entre paréntesis. Para revertir:
       DROP VIEW IF EXISTS V_ACRED_CICLO, V_ACRED_CASO, V_ACRED_ESTADO_CLASIF;
   ============================================================================= */


/* -----------------------------------------------------------------------------
   01.1 · CLASIFICACIÓN DE ESTADOS
   ⚠ AJUSTAR con el resultado real de la query 00.1 antes de dar por buenos los KPIs.
   El orden de los WHEN importa: 'NO ACREDITADO' y 'DESACREDITADO' se atrapan
   ANTES que el patrón genérico '%ACREDITAD%'.
----------------------------------------------------------------------------- */
CREATE OR REPLACE VIEW V_ACRED_ESTADO_CLASIF AS
SELECT
    e.ID_ESTADO_ACREDITACION,
    e.DESCRIPCION,
    CASE
        WHEN UPPER(e.DESCRIPCION) LIKE '%NO ACREDITAD%'   THEN 'RECHAZADO'
        WHEN UPPER(e.DESCRIPCION) LIKE '%DESACREDITAD%'   THEN 'BAJA'
        WHEN UPPER(e.DESCRIPCION) LIKE '%RECHAZ%'         THEN 'RECHAZADO'
        WHEN UPPER(e.DESCRIPCION) LIKE '%OBSERV%'         THEN 'RECHAZADO'
        WHEN UPPER(e.DESCRIPCION) LIKE '%BLOQUE%'         THEN 'RECHAZADO'
        WHEN UPPER(e.DESCRIPCION) LIKE '%DEVUEL%'         THEN 'RECHAZADO'
        WHEN UPPER(e.DESCRIPCION) LIKE '%ACREDITAD%'      THEN 'APROBADO'
        WHEN UPPER(e.DESCRIPCION) LIKE '%APROBAD%'        THEN 'APROBADO'
        WHEN UPPER(e.DESCRIPCION) LIKE '%HABILITAD%'      THEN 'APROBADO'
        WHEN UPPER(e.DESCRIPCION) LIKE '%VIGENTE%'        THEN 'APROBADO'
        WHEN UPPER(e.DESCRIPCION) LIKE '%FINIQUIT%'       THEN 'BAJA'
        WHEN UPPER(e.DESCRIPCION) LIKE '%DESVINCUL%'      THEN 'BAJA'
        WHEN UPPER(e.DESCRIPCION) LIKE '%SUSPEND%'        THEN 'BAJA'
        WHEN UPPER(e.DESCRIPCION) LIKE '%INACTIV%'        THEN 'BAJA'
        WHEN UPPER(e.DESCRIPCION) LIKE '%PENDIENTE%'      THEN 'EN_PROCESO'
        WHEN UPPER(e.DESCRIPCION) LIKE '%REVIS%'          THEN 'EN_PROCESO'
        WHEN UPPER(e.DESCRIPCION) LIKE '%TRAMITE%'        THEN 'EN_PROCESO'
        WHEN UPPER(e.DESCRIPCION) LIKE '%TR_MITE%'        THEN 'EN_PROCESO'
        WHEN UPPER(e.DESCRIPCION) LIKE '%PROCESO%'        THEN 'EN_PROCESO'
        WHEN UPPER(e.DESCRIPCION) LIKE '%ESPERA%'         THEN 'EN_PROCESO'
        ELSE 'OTRO'
    END AS GRUPO_ESTADO,
    /* TERMINAL = evento que cierra un ciclo de revisión */
    CASE
        WHEN UPPER(e.DESCRIPCION) LIKE '%NO ACREDITAD%' THEN 1
        WHEN UPPER(e.DESCRIPCION) LIKE '%DESACREDITAD%' THEN 0
        WHEN UPPER(e.DESCRIPCION) LIKE '%RECHAZ%'
          OR UPPER(e.DESCRIPCION) LIKE '%OBSERV%'
          OR UPPER(e.DESCRIPCION) LIKE '%BLOQUE%'
          OR UPPER(e.DESCRIPCION) LIKE '%DEVUEL%'
          OR UPPER(e.DESCRIPCION) LIKE '%ACREDITAD%'
          OR UPPER(e.DESCRIPCION) LIKE '%APROBAD%'
          OR UPPER(e.DESCRIPCION) LIKE '%HABILITAD%'
          OR UPPER(e.DESCRIPCION) LIKE '%VIGENTE%'      THEN 1
        ELSE 0
    END AS ES_TERMINAL
FROM DB_LEGAV_ESTATUS_ACREDITACION e;


/* -----------------------------------------------------------------------------
   01.2 · V_ACRED_CICLO  ·  GRANO = UNA SOLICITUD (una "vuelta" de revisión)
   Mide el SLA operativo del acreditador: cuánto tarda en responder cada envío.

   Desenlace del ciclo = PRIMER evento terminal (aprobado o rechazado) posterior
   a la fecha de solicitud. Así una solicitud rechazada NO hereda la fecha de
   aprobación de un ciclo posterior (error clásico que infla el lead time).
----------------------------------------------------------------------------- */
CREATE OR REPLACE VIEW V_ACRED_CICLO AS
SELECT
    sol.ID_SOLICITUD,
    sol.ID_ASIGNACION,
    asg.ID_PERSONA,
    per.RUT                                             AS RUT_TRABAJADOR,
    TRIM(CONCAT_WS(' ', per.NOMBRE, per.APELLIDO))      AS TRABAJADOR,
    per.CARGO,
    per.SEXO,
    emp.ID_EMPRESA,
    emp.RUT                                             AS RUT_EMPRESA,
    COALESCE(emp.NOMBRE_FANTASIA, emp.NOMBRE)           AS EMPRESA,
    con.ID_REG_CONTRATO,
    con.NUMERO_ACUERDO,
    con.DESCRIPCION                                     AS CONTRATO,
    con.ESTADO                                          AS ESTADO_CONTRATO,
    man.ID_MANDANTE,
    man.NOMBRE_FAENA                                    AS MANDANTE,
    ger.DESCRIPCION                                     AS GERENCIA,
    act.DESCRIPCION                                     AS ACTIVIDAD,

    /* ---- hitos temporales del ciclo ---- */
    sol.FECHA_REGISTRO                                  AS FECHA_SOLICITUD,
    sol.FECHA_REVISION,
    est.FECHA_REGISTRO                                  AS FECHA_DESENLACE,
    cls.GRUPO_ESTADO                                    AS RESULTADO_CICLO,
    cls.DESCRIPCION                                     AS ESTADO_DESENLACE,
    est.OBSERVACION                                     AS OBS_DESENLACE,
    est.ID_DOCUMENTO_BLOQUEO,
    doc.NOMBRE                                          AS DOCUMENTO_BLOQUEO,
    est.ID_USU_LEGAV                                    AS ID_REVISOR,
    TRIM(CONCAT_WS(' ', adm.NOMBRE, adm.APELLIDO))      AS REVISOR,

    /* ---- métricas de tiempo del ciclo ---- */
    TIMESTAMPDIFF(HOUR, sol.FECHA_REGISTRO, est.FECHA_REGISTRO)   AS HORAS_CICLO,
    ROUND(TIMESTAMPDIFF(HOUR, sol.FECHA_REGISTRO, est.FECHA_REGISTRO)/24, 2)
                                                                  AS DIAS_CICLO,
    TIMESTAMPDIFF(HOUR, sol.FECHA_REGISTRO, sol.FECHA_REVISION)   AS HORAS_HASTA_REVISION,

    /* ---- orden del ciclo dentro del caso: 1 = primer envío ---- */
    (SELECT COUNT(*) FROM DB_LEGAV_SOLICITUD_ACREDITACION s2
      WHERE s2.ID_ASIGNACION = sol.ID_ASIGNACION
        AND s2.FECHA_REGISTRO <= sol.FECHA_REGISTRO)              AS NRO_CICLO,

    DATE(sol.FECHA_REGISTRO)                            AS DIA_SOLICITUD,
    DATE_FORMAT(sol.FECHA_REGISTRO, '%Y-%m')            AS MES_SOLICITUD,
    DAYNAME(sol.FECHA_REGISTRO)                         AS DIA_SEMANA_SOLICITUD,
    HOUR(sol.FECHA_REGISTRO)                            AS HORA_SOLICITUD

FROM DB_LEGAV_SOLICITUD_ACREDITACION sol
JOIN      DB_LEGAV_ASIG_PERSONAL_ACUERDO asg ON asg.ID_ASIGNACION  = sol.ID_ASIGNACION
LEFT JOIN DB_LEGAV_PERSONAL_ACREDITACION per ON per.ID_PERSONA     = asg.ID_PERSONA
LEFT JOIN DB_LEGAV_CONTRATO_EMP          con ON con.ID_REG_CONTRATO= asg.ID_REG_ACUERDOS
LEFT JOIN DB_LEGAV_EMPRESA               emp ON emp.ID_EMPRESA     = COALESCE(con.ID_EMPRESA, per.ID_EMPRESA)
LEFT JOIN DB_LEGAV_MANDANTE              man ON man.ID_MANDANTE    = con.ID_MANDANTE
LEFT JOIN DB_LEGAV_MAN_GERENCIA_DETALLE  gd  ON gd.ID_DETALLE_GERENCIA = con.ID_DETALLE_GERENCIA
LEFT JOIN DB_LEGAV_MANDANTE_GERENCIA     ger ON ger.ID_GERENCIA    = gd.ID_GERENCIA
LEFT JOIN DB_LEGAV_ACTIVIDAD_TRABAJADOR_MANDANTE act ON act.ID_ACTIVIDAD = asg.ID_ACTIVIDAD

/* Primer evento terminal posterior a la solicitud.
   Se resuelve por MIN(ID_ESTATUS) y no por MIN(FECHA): ID_ESTATUS es
   AUTO_INCREMENT, así que identifica UNA fila exacta y evita que dos estados
   con el mismo timestamp dupliquen el ciclo. */
LEFT JOIN (
    SELECT  s.ID_SOLICITUD,
            MIN(e.ID_ESTATUS) AS ID_ESTATUS_DESENLACE
    FROM DB_LEGAV_SOLICITUD_ACREDITACION s
    JOIN DB_LEGAV_STATUS_ACREDITACION_PERSONA e
          ON e.ID_ASIGNACION  = s.ID_ASIGNACION
         AND e.FECHA_REGISTRO >= s.FECHA_REGISTRO
    JOIN V_ACRED_ESTADO_CLASIF c
          ON c.ID_ESTADO_ACREDITACION = e.ID_ESTADO_ACREDITACION
         AND c.ES_TERMINAL = 1
    WHERE s.FECHA_REGISTRO IS NOT NULL
    GROUP BY s.ID_SOLICITUD
) d ON d.ID_SOLICITUD = sol.ID_SOLICITUD

/* fila de estado correspondiente a ese desenlace */
LEFT JOIN DB_LEGAV_STATUS_ACREDITACION_PERSONA est
       ON est.ID_ESTATUS = d.ID_ESTATUS_DESENLACE
LEFT JOIN V_ACRED_ESTADO_CLASIF cls ON cls.ID_ESTADO_ACREDITACION = est.ID_ESTADO_ACREDITACION
LEFT JOIN DB_LEGAV_ADMINISTRATIVOS  adm ON adm.ID_USU_LEGAV = est.ID_USU_LEGAV
LEFT JOIN DB_DOCUMENTO_ESTANDAR_ACREDITACION doc ON doc.ID_DOCUMENTO = est.ID_DOCUMENTO_BLOQUEO
WHERE sol.FECHA_REGISTRO IS NOT NULL;


/* -----------------------------------------------------------------------------
   01.3 · V_ACRED_CASO  ·  GRANO = UNA ASIGNACIÓN (el trabajador punta a punta)
   Es el lead time que vive el trabajador y que reclama la EECC:
   primera solicitud → primera aprobación, con todo el retrabajo dentro.
----------------------------------------------------------------------------- */
CREATE OR REPLACE VIEW V_ACRED_CASO AS
SELECT
    asg.ID_ASIGNACION,
    asg.ID_PERSONA,
    per.RUT                                             AS RUT_TRABAJADOR,
    TRIM(CONCAT_WS(' ', per.NOMBRE, per.APELLIDO))      AS TRABAJADOR,
    per.CARGO,
    asg.PERSONAL_ACTIVO,
    emp.ID_EMPRESA,
    COALESCE(emp.NOMBRE_FANTASIA, emp.NOMBRE)           AS EMPRESA,
    con.ID_REG_CONTRATO,
    con.NUMERO_ACUERDO,
    con.DESCRIPCION                                     AS CONTRATO,
    man.ID_MANDANTE,
    man.NOMBRE_FAENA                                    AS MANDANTE,
    ger.DESCRIPCION                                     AS GERENCIA,

    asg.FECHA_REGISTRO                                  AS FECHA_ASIGNACION,
    sol.F_PRIMERA_SOLICITUD,
    sol.F_ULTIMA_SOLICITUD,
    sol.N_SOLICITUDES,
    ap.F_APROBACION,
    COALESCE(rz.N_RECHAZOS, 0)                          AS N_RECHAZOS,
    COALESCE(ult.ESTADO_ACTUAL, '(sin estado registrado)') AS ESTADO_ACTUAL,
    COALESCE(ult.GRUPO_ACTUAL,  'SIN_ESTADO')              AS GRUPO_ACTUAL,
    ult.F_ULTIMO_ESTADO,

    /* ---- KPI PRINCIPAL: lead time punta a punta ---- */
    TIMESTAMPDIFF(HOUR, sol.F_PRIMERA_SOLICITUD, ap.F_APROBACION)          AS HORAS_TOTAL,
    ROUND(TIMESTAMPDIFF(HOUR, sol.F_PRIMERA_SOLICITUD, ap.F_APROBACION)/24, 2)
                                                                          AS DIAS_TOTAL,
    /* ---- tiempo del último envío: cuánto habría tardado sin retrabajo ---- */
    ROUND(TIMESTAMPDIFF(HOUR, sol.F_ULTIMA_SOLICITUD, ap.F_APROBACION)/24, 2)
                                                                          AS DIAS_ULTIMO_ENVIO,
    /* ---- preparación documental de la EECC (antes de la 1ª solicitud) ---- */
    ROUND(TIMESTAMPDIFF(HOUR, asg.FECHA_REGISTRO, sol.F_PRIMERA_SOLICITUD)/24, 2)
                                                                          AS DIAS_PREPARACION,
    /* ---- reloj partido: quién consume el tiempo ---- */
    ROUND(cic.HORAS_EN_MANDANTE/24, 2)                                    AS DIAS_EN_MANDANTE,
    ROUND((TIMESTAMPDIFF(HOUR, sol.F_PRIMERA_SOLICITUD, ap.F_APROBACION)
           - cic.HORAS_EN_MANDANTE)/24, 2)                                AS DIAS_EN_CONTRATISTA,

    CASE WHEN ap.F_APROBACION IS NULL THEN 'ABIERTO' ELSE 'CERRADO' END   AS ESTADO_CASO,
    ROUND(TIMESTAMPDIFF(HOUR, sol.F_PRIMERA_SOLICITUD, NOW())/24, 2)      AS DIAS_ANTIGUEDAD,
    DATE_FORMAT(sol.F_PRIMERA_SOLICITUD, '%Y-%m')                         AS MES_SOLICITUD,
    DATE_FORMAT(ap.F_APROBACION,        '%Y-%m')                          AS MES_APROBACION

FROM DB_LEGAV_ASIG_PERSONAL_ACUERDO asg
JOIN (
    SELECT ID_ASIGNACION,
           MIN(FECHA_REGISTRO) AS F_PRIMERA_SOLICITUD,
           MAX(FECHA_REGISTRO) AS F_ULTIMA_SOLICITUD,
           COUNT(*)            AS N_SOLICITUDES
    FROM DB_LEGAV_SOLICITUD_ACREDITACION
    WHERE FECHA_REGISTRO IS NOT NULL
    GROUP BY ID_ASIGNACION
) sol ON sol.ID_ASIGNACION = asg.ID_ASIGNACION

LEFT JOIN DB_LEGAV_PERSONAL_ACREDITACION per ON per.ID_PERSONA      = asg.ID_PERSONA
LEFT JOIN DB_LEGAV_CONTRATO_EMP          con ON con.ID_REG_CONTRATO = asg.ID_REG_ACUERDOS
LEFT JOIN DB_LEGAV_EMPRESA               emp ON emp.ID_EMPRESA      = COALESCE(con.ID_EMPRESA, per.ID_EMPRESA)
LEFT JOIN DB_LEGAV_MANDANTE              man ON man.ID_MANDANTE     = con.ID_MANDANTE
LEFT JOIN DB_LEGAV_MAN_GERENCIA_DETALLE  gd  ON gd.ID_DETALLE_GERENCIA = con.ID_DETALLE_GERENCIA
LEFT JOIN DB_LEGAV_MANDANTE_GERENCIA     ger ON ger.ID_GERENCIA     = gd.ID_GERENCIA

/* primera aprobación posterior a la primera solicitud */
LEFT JOIN (
    SELECT e.ID_ASIGNACION, MIN(e.FECHA_REGISTRO) AS F_APROBACION
    FROM DB_LEGAV_STATUS_ACREDITACION_PERSONA e
    JOIN V_ACRED_ESTADO_CLASIF c ON c.ID_ESTADO_ACREDITACION = e.ID_ESTADO_ACREDITACION
    WHERE c.GRUPO_ESTADO = 'APROBADO'
    GROUP BY e.ID_ASIGNACION
) ap ON ap.ID_ASIGNACION = asg.ID_ASIGNACION

/* nº de rechazos acumulados */
LEFT JOIN (
    SELECT e.ID_ASIGNACION, COUNT(*) AS N_RECHAZOS
    FROM DB_LEGAV_STATUS_ACREDITACION_PERSONA e
    JOIN V_ACRED_ESTADO_CLASIF c ON c.ID_ESTADO_ACREDITACION = e.ID_ESTADO_ACREDITACION
    WHERE c.GRUPO_ESTADO = 'RECHAZADO'
    GROUP BY e.ID_ASIGNACION
) rz ON rz.ID_ASIGNACION = asg.ID_ASIGNACION

/* horas efectivas en cancha del mandante = suma de los ciclos de revisión */
LEFT JOIN (
    SELECT ID_ASIGNACION, SUM(HORAS_CICLO) AS HORAS_EN_MANDANTE
    FROM V_ACRED_CICLO
    WHERE HORAS_CICLO IS NOT NULL AND HORAS_CICLO >= 0
    GROUP BY ID_ASIGNACION
) cic ON cic.ID_ASIGNACION = asg.ID_ASIGNACION

/* estado vigente hoy */
LEFT JOIN (
    SELECT e.ID_ASIGNACION, c.DESCRIPCION AS ESTADO_ACTUAL,
           c.GRUPO_ESTADO AS GRUPO_ACTUAL, e.FECHA_REGISTRO AS F_ULTIMO_ESTADO
    FROM DB_LEGAV_STATUS_ACREDITACION_PERSONA e
    JOIN V_ACRED_ESTADO_CLASIF c ON c.ID_ESTADO_ACREDITACION = e.ID_ESTADO_ACREDITACION
    JOIN (
        SELECT ID_ASIGNACION, MAX(ID_ESTATUS) AS ID_ESTATUS
        FROM DB_LEGAV_STATUS_ACREDITACION_PERSONA
        GROUP BY ID_ASIGNACION
    ) m ON m.ID_ESTATUS = e.ID_ESTATUS
) ult ON ult.ID_ASIGNACION = asg.ID_ASIGNACION;


/* -----------------------------------------------------------------------------
   01.4 · ÍNDICES RECOMENDADOS (opcional, mejora fuerte el tiempo de respuesta)
   Ejecutar solo si las queries tardan. Son índices, no cambian datos.
----------------------------------------------------------------------------- */
-- ALTER TABLE DB_LEGAV_SOLICITUD_ACREDITACION      ADD INDEX IX_SOL_ASIG_FEC (ID_ASIGNACION, FECHA_REGISTRO);
-- ALTER TABLE DB_LEGAV_STATUS_ACREDITACION_PERSONA ADD INDEX IX_EST_ASIG_FEC (ID_ASIGNACION, FECHA_REGISTRO);
-- ALTER TABLE DB_LEGAV_STATUS_ACREDITACION_PERSONA ADD INDEX IX_EST_ESTADO    (ID_ESTADO_ACREDITACION);
