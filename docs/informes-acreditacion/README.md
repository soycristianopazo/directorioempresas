# Informe de Gestión de Acreditación — `legavcl_caitan`

Pack de consultas SQL para medir **cuánto tarda un trabajador desde que se solicita
su acreditación hasta que queda aprobado**, y por qué tarda lo que tarda.

Motor objetivo: **MySQL 5.7.44**. Todo el pack está escrito sin CTEs ni funciones
de ventana (no existen en 5.7): solo tablas derivadas y subconsultas correlacionadas.

---

## 1. Modelo de datos reconstruido

Las FKs del dump confirman esta cadena. El concepto central es la **asignación**
(`ID_ASIGNACION`), que es un trabajador dentro de un contrato: ese es el "caso"
de acreditación.

```
DB_LEGAV_PERSONAL_ACREDITACION      trabajador (RUT, nombre, cargo)
        │ ID_PERSONA
        ▼
DB_LEGAV_ASIG_PERSONAL_ACUERDO      ← ID_ASIGNACION = el caso de acreditación
        │        │ ID_REG_ACUERDOS → DB_LEGAV_CONTRATO_EMP.ID_REG_CONTRATO
        │        │                        └─ EMPRESA · MANDANTE · GERENCIA
        │
        ├─► DB_LEGAV_SOLICITUD_ACREDITACION      ⏱ FECHA_REGISTRO = "se solicita"
        │                                        ⏱ FECHA_REVISION
        │
        ├─► DB_LEGAV_STATUS_ACREDITACION_PERSONA ⏱ log de estados + ID_DOCUMENTO_BLOQUEO
        │        └─ DB_LEGAV_ESTATUS_ACREDITACION (catálogo de estados)
        │
        └─► DB_LEGAV_HISTORIAL_ACREDITACION      bitácora libre
```

Ojo con una trampa del esquema: existen **dos** tablas con columna `ID_ASIGNACION`.
`DB_LEGAV_ASIGNA_DIVISION` es la asignación de un *contrato a una división*, no del
trabajador. La FK `FK_REFERENCE_46` deja claro que la acreditación cuelga de
`DB_LEGAV_ASIG_PERSONAL_ACUERDO`. Todo el pack usa esa.

Otra: `ASIG_PERSONAL_ACUERDO.ID_REG_ACUERDOS` se llama como si apuntara a un acuerdo
de jornada, pero la FK apunta a `CONTRATO_EMP.ID_REG_CONTRATO`.

---

## 2. Definición de los tiempos

Se miden en **dos granos distintos** porque responden preguntas distintas:

| Grano | Vista | Qué mide | Para quién |
|---|---|---|---|
| **Caso** | `V_ACRED_CASO` | 1ª solicitud → 1ª aprobación, con todo el retrabajo dentro | El lead time real que vive el trabajador y que reclama la EECC |
| **Ciclo** | `V_ACRED_CICLO` | cada envío → su desenlace | El SLA del equipo acreditador, aislado del retrabajo |

El **desenlace de un ciclo** es el primer evento terminal (aprobado *o* rechazado)
posterior a esa solicitud. Es importante: si se tomara simplemente "la aprobación
del trabajador", una solicitud rechazada heredaría la fecha de aprobación de un
ciclo posterior y el SLA saldría inflado.

El lead time total se descompone en tres tramos con dueño distinto:

```
FECHA_ASIGNACION ──► 1ª SOLICITUD ──► [rev] ──► rechazo ──► [corrección] ──► 2ª SOLICITUD ──► [rev] ──► APROBADO
                 └ DIAS_PREPARACION ┘ └──────── DIAS_EN_MANDANTE (suma de revisiones) ────────┘
                                       └────── DIAS_EN_CONTRATISTA (total − revisiones) ──────┘
```

Esa descomposición es la que cierra la discusión de "el mandante se demora" contra
"la contratista manda los papeles malos".

---

## 3. Orden de ejecución

| Archivo | Qué hace | Cuándo |
|---|---|---|
| `00_diagnostico.sql` | catálogo de estados, volumetría, calidad de datos | **primero, siempre** |
| `01_vistas_base.sql` | crea las 3 vistas de la capa semántica | una vez |
| `02_dataset_maestro.sql` | los 3 CSV a exportar | para armar el informe |
| `03_kpis_tiempos.sql` | KPIs de tiempo (el núcleo) | |
| `04_retrabajo_bloqueos.sql` | causas de rechazo y documentos que bloquean | |
| `05_backlog_flujo.sql` | qué está atascado hoy | |

### Paso obligatorio antes de creer cualquier número

Ejecutar **`00_diagnostico.sql` query 00.1** y revisar el catálogo real de estados.
La clasificación `APROBADO / RECHAZADO / EN_PROCESO / BAJA` de `V_ACRED_ESTADO_CLASIF`
está hecha por patrones de texto sobre `DESCRIPCION` porque el dump vino sin datos.
Es una hipótesis razonable, no un hecho: si aparece un estado que cae en `OTRO`, o
mal clasificado, se corrige el `CASE` de la vista **una sola vez** y todo el resto
del pack se ajusta solo.

Ya está resuelto el caso peligroso: `NO ACREDITADO` y `DESACREDITADO` se atrapan
*antes* que el patrón genérico `%ACREDITAD%`, así que no se cuentan como aprobación.

---

## 4. Los CSV que necesito

| Archivo | Query | Grano | Filas aprox. |
|---|---|---|---|
| `acred_casos.csv` | CSV 1 | una fila por trabajador-contrato | = nº de asignaciones con solicitud |
| `acred_ciclos.csv` | CSV 2 | una fila por envío | = nº de solicitudes |
| `acred_documentos.csv` | CSV 3 | una fila por documento cargado | = nº de archivos |

**Con `acred_casos.csv` solo ya se construye el 80% del informe.** Si son muchas
filas, descomentar el filtro de fecha en cada query.

En phpMyAdmin: ejecutar → *Exportar* → **CSV**, separador coma, "Poner los nombres
de las columnas en la primera fila", codificación **UTF-8**.

---

## 5. Qué va a contener el informe

**Portada — 6 números**
lead time mediano · P90 · % de acreditación · envíos por caso · % de retrabajo · backlog abierto

**Sección 1 · Tiempos**
- Evolución mensual: mediana y P90 sobre barras de volumen *(03.2)*
- Histograma de distribución de tiempos *(03.5)*
- Cumplimiento de SLA por mes, barras apiladas *(03.6)*
- Descomposición del lead time: preparación / revisión / corrección *(03.7)*

**Sección 2 · Dónde se pierde el tiempo**
- Impacto del retrabajo: días adicionales por cada rechazo *(04.1)*
- Pareto de documentos que bloquean *(04.2)*
- First Pass Yield mensual *(04.5)*

**Sección 3 · Actores**
- Ranking de empresas contratistas *(03.3)*
- Comparativa por mandante y gerencia *(03.4)*
- Carga y tiempo de respuesta por revisor *(03.9)*

**Sección 4 · Situación actual y acciones**
- Backlog por antigüedad *(05.1)*
- Entradas vs salidas mensuales *(05.4)*
- Embudo del proceso *(05.5)*
- **Anexo accionable**: lista nominal de casos atascados *(05.2, 05.3)*

---

## 6. Notas metodológicas

**Mediana y P90 antes que promedio.** En procesos documentales la media miente:
cuatro casos atascados 90 días arrastran el promedio de cientos que se cierran en
dos. El número para comité es el P90 — *"9 de cada 10 se acreditan en X días"*.

**Cálculo de percentiles.** MySQL 5.7 no tiene `PERCENTILE_CONT`, así que se usa
`GROUP_CONCAT` + `SUBSTRING_INDEX`. Requiere `SET SESSION group_concat_max_len =
10000000` (ya incluido en cada archivo). Devuelve la *mediana inferior*: con un
número par de casos toma el valor de abajo en vez de promediar los dos centrales.
La diferencia es irrelevante con volumen real.

**Días hábiles.** La expresión `DIAS_HABILES_TOTAL` del CSV 1 descuenta sábados y
domingos pero **no feriados chilenos**. Validada contra el fixture de prueba. Si el
SLA contractual se mide en días hábiles reales, hay que agregar una tabla
`DIM_FERIADOS` y restar; se puede armar si hace falta.

**Cortes de significancia.** Los rankings por empresa filtran con `HAVING COUNT(*) >= 5`.
Con 2 casos no hay estadística, hay anécdota.

---

## 7. Verificación realizada

El pack no se entregó a ciegas. Se levantó un servidor MySQL local, se cargó el
esquema completo del dump (114 tablas) y se ejecutaron los 6 archivos con
`sql_mode = ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,...` (el modo por defecto de
MySQL 5.7): **las 6 corren sin errores**.

Además se cargó un fixture sintético de 3 casos de control para verificar la lógica,
no solo la sintaxis:

| Caso | Escenario | Esperado | Obtenido |
|---|---|---|---|
| 1 | 1 envío, aprobado en 2 días | total 2 d, mandante 2 d, contratista 0 d | ✅ |
| 2 | envío → rechazo (1 d) → corrección (4 d) → reenvío → aprobado (1 d) | total 6 d, mandante 2 d, contratista 4 d, 2 envíos, 1 rechazo | ✅ |
| 3 | solicitado, sin desenlace | ABIERTO, sin lead time, cuenta en backlog | ✅ |

La prueba crítica es el caso 2: el ciclo 1 cierra con el **rechazo del 2-ene**, no
con la aprobación del 7-ene. Ese es el error que arruina la mayoría de los informes
de acreditación y aquí está controlado.

Una advertencia honesta: el dump venía **sin una sola fila de datos** (solo
estructura). Todo lo anterior valida sintaxis y lógica contra datos de control, no
contra la realidad de la base. Los resultados de `00_diagnostico.sql` sobre la BD
real pueden obligar a ajustar la clasificación de estados.
