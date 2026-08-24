# 05 · Mejoras propuestas al diseño

> Documento N. Veinte propuestas para llevar el diseño de "muy bueno" a "clase mundial".
> Cada una indica **qué falta**, **por qué importa** e **impacto en el modelo**.

Las cinco primeras son **correcciones**: cambian el diseño planteado en el brief. Las demás son **adiciones**.

---

## 🔧 Correcciones al diseño original

### N.1 · Separar el eje "qué vendes" del eje "a qué industria sirves"

**Qué cambia.** El brief (§7) propone `Industria → Categoría → Subcategoría → Especialidad → Servicio` como un solo árbol. Propongo dos árboles ortogonales: `taxonomy_nodes` (oferta) e `industries` (mercado).

**Por qué.** Con un solo árbol, "Transporte de personas" existe replicado bajo Minería, Construcción, Retail y Energía. El proveedor se clasifica cuatro veces, el comprador busca en cuatro ramas, y la oferta queda fragmentada justo donde el matching necesita densidad. Con dos ejes, la rama existe una vez y la experiencia sectorial se declara y evidencia por separado — lo que además habilita una señal de matching que con un eje es imposible: *vende exactamente esto Y tiene experiencia comprobada en esta industria*.

**Impacto.** Ninguno en la UI (se sigue navegando como un árbol de dos filtros). Grande en el modelo. **Si se hace, hay que hacerlo antes de la primera línea de código.**

---

### N.2 · La oferta (offering), no la empresa, es la unidad de clasificación

**Qué cambia.** Categoría, territorio, atributos, capacidad, certificaciones y precio cuelgan de `supplier_offerings`, no de `organizations`.

**Por qué.** El §44 lo pide en palabras; hay que hacerlo estructural. Una empresa de transporte que ofrece buses a faena en Antofagasta y arriendo de camionetas en Santiago tiene coberturas, atributos y capacidades distintas por servicio. Modelarlo a nivel empresa produce falsos positivos permanentes ("dice que cubre Antofagasta" — sí, pero con camionetas, no con buses).

**Impacto.** Es el habilitador del matching preciso y del Knowledge Graph. Todo el modelo D4 gira en torno a esto.

---

### N.3 · La acreditación es una relación, no un campo

**Qué cambia.** No existe `organizations.accreditation_status`. Existe `accreditation_enrollments(organization_id, program_id, status, valid_until)`.

**Por qué.** El §13 lo exige (acreditado para TI, no para eléctrico de alto riesgo). Un campo único hace imposible ese requisito y obliga a un refactor doloroso en el mes 6, cuando ya hay 500 empresas acreditadas.

**Impacto.** Un JOIN más en las consultas, a cambio de que el requisito más diferenciador del producto sea posible.

---

### N.4 · Inmutabilidad estructural de las cotizaciones

**Qué cambia.** `quotation_items` cuelga de `quotation_revisions` (append-only), no de `quotations`.

**Por qué.** El §27 y el §77 piden "nunca sobrescribir". Si la estructura permite el `UPDATE`, tarde o temprano alguien lo escribe. Si `quotation_items.revision_id` es la FK, sobrescribir es imposible por construcción: solo se puede insertar una revisión nueva. La negociación (rondas, BAFO) queda modelada gratis.

**Impacto.** Consultar "la oferta actual" pasa por `where is_current` o por `current_revision_id`. Coste trivial, garantía absoluta.

---

### N.5 · Territorio como jerarquía genérica, no como `regions` + `cities`

**Qué cambia.** Una tabla `admin_divisions` autoreferente con `path ltree`, en vez de `countries` + `regions` + `cities`.

**Por qué.** Chile tiene Región → Provincia → Comuna. Perú tiene Departamento → Provincia → Distrito. México tiene Estado → Municipio (dos niveles). Con tablas rígidas, el segundo país obliga a migrar el esquema. Además, "cobertura en la Región de Antofagasta" y "cobertura en la comuna de Sierra Gorda" son la misma relación a distinto nivel: una sola FK lo resuelve; tres tablas obligan a tres columnas nullables.

**Impacto.** Consultas de cobertura ascendente/descendente con un operador `<@` en vez de `UNION`s.

---

## ➕ Adiciones al alcance

### N.6 · Pre-carga de perfiles + flujo "Reclama tu empresa"

**Qué falta.** El brief asume que los proveedores se registran solos. Un marketplace vacío no atrae compradores, y sin compradores no se registran proveedores.

**Propuesta.** Pre-cargar 2.000–5.000 empresas desde fuentes públicas (registros de proveedores mineros, cámaras, asociaciones gremiales, datos públicos del SII), con perfil mínimo y estado `is_claimed = false`. El comprador ya encuentra algo el día 1; el proveedor descubre que "ya está" y reclama su perfil vía `organization_claims` (verificación por email de dominio corporativo + documento).

**Impacto.** `organizations.is_claimed`, `organization_claims`, `data_source`. Es probablemente la decisión más determinante del éxito comercial en los primeros seis meses.

---

### N.7 · Portabilidad del perfil: una carga, N compradores

**Qué falta.** El brief describe la acreditación desde la óptica de la plataforma. Falta nombrar explícitamente la propuesta de valor que hace que el proveedor entre.

**Propuesta.** Diseñar el repositorio documental (`organization_documents`) como **propiedad del proveedor**, reutilizable en todos los programas de todos los compradores. Un panel del proveedor que diga: *"Tu F30 vigente cubre los requisitos de 7 programas de acreditación."*

**Por qué importa.** El dolor #1 del proveedor en Chile no es que no lo encuentren: es subir los mismos 14 documentos en 9 portales distintos cada mes. Resolver eso es la cuña de adopción, más incluso que la visibilidad.

**Impacto.** Ya está en el modelo (D5/D6). Falta hacerlo explícito como *feature de marketing*, con su propia pantalla.

---

### N.8 · Metodología de ahorro definida y auditable

**Qué falta.** El §29 pide "ahorros" sin definir cómo se calculan. Un número de ahorro que el CFO no puede reproducir destruye credibilidad.

**Propuesta.** `awards.baseline_amount` + `baseline_method ∈ {PREVIOUS_AWARD, BUDGET, FIRST_OFFER_AVG, HIGHEST_OFFER, MANUAL}` + `savings_amount` derivado. La UI obliga a elegir el método y lo muestra siempre junto al número.

**Impacto.** 3 columnas. Convierte una métrica de vanidad en un reporte defendible ante auditoría.

---

### N.9 · Workflow de aprobación (Delegation of Authority)

**Qué falta.** El brief no contempla que en una empresa grande el jefe de abastecimiento no puede adjudicar $2.000 millones solo.

**Propuesta.** `organization_approval_policies` (umbrales por monto y categoría) + `award_approvals` (cadena de aprobadores con estado y comentario). Sin esto, ninguna empresa mediana o grande puede usar la adjudicación de la plataforma como registro oficial: la seguirán haciendo por correo.

**Impacto.** 2 tablas + `organization_members.approval_limit_amount`. Requisito de venta enterprise.

---

### N.10 · Modo sellado y ceremonia de apertura

**Qué falta.** El brief no distingue entre ofertas abiertas y selladas.

**Propuesta.** `sourcing_events.bid_mode ∈ {OPEN, SEALED}`, `bid_opened_at`, `bid_opened_by`, y **RLS que impide leer montos antes de la apertura**, incluso al dueño del evento. Apertura registrada en `audit_logs`.

**Por qué.** Es un requisito legal y de compliance en el mundo minero, energético y público. Además es un diferenciador de confianza fuerte frente a la cotización por correo.

**Impacto.** 3 columnas + la policy más cuidada del sistema.

---

### N.11 · Separación de deberes en la evaluación

**Qué falta.** El §25 separa evaluación técnica y económica, pero no impide que el evaluador técnico vea el precio.

**Propuesta.** `evaluation_assignments.can_view_commercial = false` para evaluadores técnicos, forzado en RLS. La evaluación técnica se cierra antes de que se revele la económica.

**Por qué.** Es la práctica estándar en licitaciones serias. Sin esto, el score técnico está contaminado y todo el comparador pierde valor.

---

### N.12 · Reviews verificadas por transacción real

**Qué falta.** El §30 permite evaluar; no restringe quién puede.

**Propuesta.** `supplier_performance_reviews` **exige** `award_id` o `contract_id`. Solo evalúa quien compró de verdad. Badge "Evaluación verificada". Cero reviews anónimas.

**Por qué.** Un sistema de reputación manipulable es peor que no tener reputación: contamina el matching y destruye la confianza que es el activo del producto.

---

### N.13 · Motivos de rechazo estructurados

**Qué falta.** `invitation.decline_reason` como texto libre no sirve para nada.

**Propuesta.** `decline_reason_code` con catálogo: `SIN_CAPACIDAD`, `FUERA_DE_ALCANCE`, `PLAZO_INSUFICIENTE`, `PRECIO_OBJETIVO_INVIABLE`, `CONDICIONES_PAGO`, `ZONA_NO_CUBIERTA`, `NO_ACREDITADO`, `OTRO`.

**Por qué.** Es la fuente de inteligencia más valiosa y más barata del marketplace: dice exactamente por qué las RFQ no reciben ofertas. Alimenta el diagnóstico de liquidez (§69) y permite avisar al comprador *"el 60% declinó por plazo insuficiente"*.

---

### N.14 · Market intelligence anonimizado

**Qué falta.** El §70 menciona "market intelligence" sin definirlo.

**Propuesta.** Agregados anonimizados por categoría y región, publicados solo con `n ≥ 5` para impedir reidentificación:
- rango de precios de adjudicaciones recientes (P25/P50/P75)
- número de proveedores elegibles
- tiempo mediano de sourcing
- número medio de ofertas por RFQ

**Por qué.** Es el dato por el que un gerente de abastecimiento paga y al que entra aunque esa semana no compre nada. Y para el proveedor: *"tu precio quedó 18% sobre la mediana de la categoría"* — feedback accionable que no revela ninguna oferta específica.

**Impacto.** `marketplace_metrics_daily` + reglas de k-anonimato explícitas.

---

### N.15 · Outbox de eventos de dominio

**Qué falta.** El brief no define cómo se disparan notificaciones, analítica e integraciones.

**Propuesta.** Tabla `domain_events` como único punto de emisión. Los triggers escriben ahí; workers consumen. Notificaciones, webhooks, analítica y (futuro) sincronización con ERPs son consumidores.

**Por qué.** Evita el anti-patrón de triggers que envían emails dentro de la transacción, permite reintentos y reproducción, y hace que agregar WhatsApp sea agregar un adaptador y no tocar 30 triggers.

---

### N.16 · Mapeo a estándares (UNSPSC)

**Qué falta.** Interoperabilidad con los ERPs de los clientes grandes.

**Propuesta.** `taxonomy_external_mappings` con UNSPSC / CPC desde el inicio, poblado progresivamente.

**Por qué.** Toda minera grande clasifica su gasto en UNSPSC. Sin ese mapeo, integrar spend analytics con SAP es un proyecto; con él es una consulta. Agregarlo después obliga a re-mapear miles de nodos a mano.

---

### N.17 · Detección proactiva de gaps de oferta

**Qué falta.** Nadie vigila las categorías donde la demanda no encuentra oferta.

**Propuesta.** Job que cruza `search_logs` + `match_results` + `sourcing_events` sin ofertas y produce un ranking de categorías/regiones con demanda insatisfecha. Alimenta directamente al equipo comercial: *"12 búsquedas de 'mantención de correas' en Calama este mes, 1 proveedor elegible"*.

**Por qué.** Convierte el crecimiento de la oferta de intuición a proceso dirigido por datos. Es la operación central de un marketplace en fase de construcción de liquidez.

---

### N.18 · Bandeja de trabajo del comprador (Sourcing Inbox)

**Qué falta.** El §62 describe un dashboard con botones. Falta lo que hace que la herramienta se use a diario.

**Propuesta.** Una bandeja priorizada: consultas sin responder, ofertas por vencer, evaluaciones pendientes, aprobaciones a la espera, documentos de proveedores críticos por vencer, RFQ sin ofertas a 48 h del cierre.

**Por qué.** El dashboard de KPIs se mira una vez al mes. La bandeja de trabajo se mira todos los días. Esa diferencia es la retención.

---

### N.19 · Entitlements en lugar de condicionales por plan

**Qué falta.** Definir cómo se aplican los límites del plan.

**Propuesta.** `plan_entitlements(plan_id, feature_code, limit_value, is_unlimited)` + `usage_counters`. En el código: `assertEntitlement(org, 'rfq.create')`. Nunca `if (plan === 'PRO')`.

**Por qué.** Los planes cambian cada trimestre en un SaaS joven. Con entitlements, cambiar un plan es un `UPDATE`. Con condicionales, es un deploy y una cacería de `if`s.

---

### N.20 · Muro entre patrocinio y ranking orgánico

**Qué falta.** El §58 lo advierte correctamente; falta hacerlo estructural.

**Propuesta.** `sponsored_placements` es una tabla **separada** de `match_results`. La API de búsqueda devuelve dos arrays distintos (`organic[]`, `sponsored[]`). La UI los renderiza en bloques separados con etiqueta "Patrocinado". Ningún componente del `supplier_score` ni del match score lee el plan.

**Por qué.** El día que un comprador sospeche que el "96% de compatibilidad" se compra, el producto perdió su razón de existir. Que sea imposible por arquitectura vale más que una política escrita.

---

## Cuadro resumen

| # | Mejora | Tipo | Fase | Coste | Impacto |
|---|---|---|---|---|---|
| N.1 | Dos ejes: oferta vs. industria | Corrección | Fase 2 | Medio | 🔴 Crítico |
| N.2 | Offering como unidad atómica | Corrección | Fase 3 | Medio | 🔴 Crítico |
| N.3 | Acreditación como relación | Corrección | Fase 5 | Bajo | 🔴 Crítico |
| N.4 | Cotizaciones inmutables | Corrección | Fase 7 | Bajo | 🔴 Crítico |
| N.5 | `admin_divisions` genérico | Corrección | Fase 2 | Bajo | 🟠 Alto |
| N.6 | Pre-carga + reclamo de perfil | Adición | MVP | Alto | 🔴 Crítico (comercial) |
| N.7 | Portabilidad del perfil | Adición | MVP | Bajo | 🔴 Crítico (adopción) |
| N.8 | Metodología de ahorro | Adición | V1 | Bajo | 🟠 Alto |
| N.9 | Workflow de aprobación (DoA) | Adición | V1 | Medio | 🟠 Alto (enterprise) |
| N.10 | Modo sellado + apertura | Adición | V1 | Medio | 🔴 Crítico (confianza) |
| N.11 | Separación de deberes | Adición | V1 | Bajo | 🟠 Alto |
| N.12 | Reviews verificadas | Adición | V2 | Bajo | 🔴 Crítico (confianza) |
| N.13 | Motivos de rechazo codificados | Adición | V1 | Muy bajo | 🟠 Alto (inteligencia) |
| N.14 | Market intelligence anonimizado | Adición | V2 | Medio | 🟠 Alto (retención) |
| N.15 | Outbox de eventos | Adición | Fase 1 | Bajo | 🟠 Alto |
| N.16 | Mapeo UNSPSC | Adición | Fase 2 | Bajo | 🟡 Medio |
| N.17 | Detección de gaps de oferta | Adición | V1 | Bajo | 🟠 Alto (crecimiento) |
| N.18 | Sourcing Inbox | Adición | V1 | Medio | 🟠 Alto (retención) |
| N.19 | Entitlements | Adición | V1 | Bajo | 🟡 Medio |
| N.20 | Muro patrocinio/orgánico | Adición | MVP | Muy bajo | 🔴 Crítico (confianza) |

---

## Las cinco que no se pueden dejar para después

Si hay que priorizar, estas cinco cambian el esquema de base y **no se pueden retrofitear sin migrar datos productivos**:

1. **N.1** — dos ejes de clasificación
2. **N.2** — offering como unidad atómica
3. **N.3** — acreditación como relación
4. **N.4** — cotizaciones inmutables
5. **N.5** — territorio jerárquico genérico

Las quince restantes se pueden incorporar en su fase sin dolor.
