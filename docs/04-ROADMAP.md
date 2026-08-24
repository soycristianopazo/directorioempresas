# 04 · Alcance, Roadmap y Riesgos

> Documentos K + L + M del diseño técnico.

---

## K. Separación de alcance: MVP / V1 / V2 / V3

### Criterio de corte

El MVP no es "la versión chica de todo". Es **la versión mínima que resuelve un problema completo para un lado del mercado**. En un marketplace B2B el orden importa: sin oferta cargada y verificable no hay nada que buscar, y sin algo que buscar el comprador no vuelve.

Por eso el MVP es **supply-side + discovery**: el proveedor construye su perfil y el comprador lo encuentra. El ciclo transaccional (RFQ → cotización → adjudicación) llega en V1, cuando ya hay densidad de oferta que invitar.

---

### 🟢 MVP — "Encuéntrame" (semanas 1–10)

**Promesa al proveedor:** *"Publica lo que vendes y aparece cuando alguien lo busca."*
**Promesa al comprador:** *"Encuentra proveedores específicos y verificados sin llamar a cinco conocidos."*

| Módulo | Alcance |
|---|---|
| Auth y cuentas | Registro, login, recuperación, verificación de email. Supabase Auth. |
| Multitenancy | Organizaciones, miembros, roles base (`ORG_OWNER`, `ORG_ADMIN`, `SUPPLIER_ADMIN`, `BUYER`, `VIEWER`), selector de organización activa. |
| Perfil de empresa | Identificación, RUT con validación de dígito verificador, contactos, ubicaciones, media, descripciones, industrias, `completion_pct`. |
| Taxonomía | Árbol `taxonomy_nodes` + `industries` + `admin_divisions` de Chile, con seed. Backoffice de administración. |
| Atributos dinámicos | `attribute_definitions`, asignación por nodo, formularios generados. **Se construye completo en el MVP** — meterlo después obliga a re-capturar todos los datos ya cargados. |
| Catálogo | `supplier_offerings` con clasificación, territorios, atributos, media, precio referencial opcional. |
| Cobertura territorial | Selector jerárquico de comunas/provincias/regiones con tipo de cobertura. |
| Búsqueda | FTS en español (unaccent + trigram) + filtros facetados sobre el read model. Discovery con filtros laterales. |
| Perfil público | `/proveedores/[slug]` indexable, con control de visibilidad por bloque. SEO: sitemap, JSON-LD `Organization`, OG tags. |
| Acreditación básica | Un solo programa de plataforma. Carga de documentos, vencimientos, revisión manual desde backoffice, estados, completitud por sección. |
| Badges | 4 badges automáticos: Verificada, Acreditada, Documentación vigente, Empresa local. |
| Onboarding proveedor | Wizard de 8 pasos con guardado parcial y barra de completitud. |
| Contacto | Botón "Contactar" → formulario que genera un lead y notifica. **Sin mensajería completa aún.** |
| Notificaciones | In-app + email transaccional (Resend). |
| Analítica proveedor v0 | Visitas al perfil, apariciones en búsqueda, contactos recibidos. |
| Backoffice | Empresas, usuarios, taxonomía, atributos, tipos de documento, revisión de acreditación. |
| Seguridad | RLS completa + suite pgTAP + auditoría. |

**Fuera del MVP, explícitamente:** RFQ, cotizaciones, matching, mensajería, evaluaciones, contratos, pagos, IA.

**Métricas de salida:** ≥ 300 proveedores con perfil ≥ 70% completo · ≥ 1.500 offerings clasificados · ≥ 60% de las categorías con ≥ 3 proveedores · ≥ 40 compradores con búsquedas recurrentes.

---

### 🔵 V1 — "Cotiza aquí" (semanas 11–22)

**Promesa:** *el ciclo transaccional completo dentro de la plataforma.*

| Módulo | Alcance |
|---|---|
| Requerimientos | Formulario estructurado + intake desde Discovery ("cotizar a estos 6"). |
| Criterios MUST/NICE | Constructor de criterios sobre atributos, certificaciones, territorio, acreditación. |
| Matching Engine v1 | Las 4 etapas completas, con explicabilidad y preview de pesos. |
| Sourcing events | RFI / RFQ / RFP / compra rápida. Visibilidad, modo sellado, hitos. |
| Invitaciones | Automáticas por match, manuales, desde listas. Máquina de estados + historial. |
| Q&A | Consultas privadas y públicas con anonimización del autor. |
| NDA | Requisito por evento, aceptación registrada con hash. |
| Cotizaciones | `quotations` + revisiones inmutables + líneas + respuestas a criterios + adjuntos. Multi-moneda con UF/UTM. |
| Comparador | Tabla horizontal, ponderación configurable, scoring de apoyo, exportación a Excel/PDF. |
| Evaluación | Plantillas, criterios por dimensión, comité, bloqueo económico para evaluadores técnicos. |
| Negociación | Rondas, contraofertas, BAFO. Historial completo. |
| Adjudicación | Awards, adjudicación parcial por lote, cadena de aprobación (DoA), notificación a todos los participantes. |
| Mensajería | Conversaciones con contexto tipado, adjuntos, lecturas, Realtime. |
| Oportunidades | Feed de oportunidades públicas para proveedores según sus categorías + alertas. |
| Vendor List | AVL del comprador con estados propios, notas privadas, código interno. |
| Analítica v1 | Dashboards de comprador y proveedor con las métricas del §39/§40. |
| Suscripciones | Planes, entitlements, límites de uso. Sin pasarela de pago aún (facturación manual). |

**Métricas de salida:** ≥ 100 RFQ creadas/mes · ≥ 3,5 cotizaciones promedio por RFQ · < 15% de RFQ sin ofertas · mediana de tiempo a primera oferta < 48 h.

---

### 🟣 V2 — "Gestiona y decide mejor" (semanas 23–36)

| Módulo | Alcance |
|---|---|
| Acreditación diferenciada | Programas por comprador, por categoría y por industria. Homologación cruzada. |
| Desempeño | Evaluación post-contrato en 8 dimensiones, solo para compras reales. |
| Supplier Score | Fórmula completa, snapshots históricos, desglose y recomendaciones. |
| Supplier 360° | Ficha consolidada de inteligencia de proveedor. |
| Contratos | Contratos, hitos, SLA, garantías, vencimientos, renovaciones. |
| Spend analytics | Gasto por categoría, región, proveedor. Concentración. Ahorros con metodología explícita. |
| Market intelligence | Rangos de precio anonimizados por categoría, densidad de oferta, tiempos de mercado. |
| Búsquedas guardadas | Alertas de nuevos proveedores compatibles. |
| IA fase 1 | Structured intake de texto libre + asistente de redacción de RFQ. |
| Búsqueda semántica | `pgvector` + re-ranking dentro del conjunto elegible. |
| Pagos | Pasarela, facturación automática, ciclo de suscripción. |
| Móvil | PWA con notificaciones push. |

---

### ⚫ V3 — "Ecosistema"

Subasta inversa · integraciones ERP (SAP/Oracle/Ariba) y API pública · due diligence y screening de sanciones · compliance (beneficiario final, conflictos de interés) · multi-país (Perú, Colombia, México) · Supplier Knowledge Graph con inferencia · marketplace de servicios financieros (factoring sobre contratos adjudicados).

---

## L. Orden exacto de desarrollo

Regla: **nunca construir una funcionalidad cuya dependencia no exista y esté probada.** Cada bloque termina con migración aplicada, tipos generados, RLS probada y documentación actualizada.

### Fase 0 — Fundaciones (semana 1)

| # | Tarea |
|---|---|
| 0.1 | Repo, Next.js 15 + TS strict + Tailwind + shadcn/ui. ESLint, Prettier, Husky. |
| 0.2 | Proyecto Supabase (local con CLI + staging + prod). Extensiones: `ltree`, `pg_trgm`, `unaccent`, `pgcrypto`, `pg_cron`. |
| 0.3 | Pipeline de migraciones + generación automática de tipos (`supabase gen types`). |
| 0.4 | Convenciones base: triggers `set_updated_at`, funciones de auditoría, ENUMs raíz. |
| 0.5 | Estructura `src/server/{repositories,services,policies,schemas,mappers}`. |
| 0.6 | CI: typecheck + lint + migraciones + pgTAP. Bloquea merge. |

### Fase 1 — Identidad y tenancy (semanas 2–3)

| # | Tarea | Depende de |
|---|---|---|
| 1.1 | `profiles` + trigger desde `auth.users` | 0.4 |
| 1.2 | `organizations`, `organization_capabilities`, `organization_legal_identifiers` | 1.1 |
| 1.3 | `roles`, `permissions`, `role_permissions`, `member_roles`, `organization_members` | 1.2 |
| 1.4 | Funciones helper RLS (`is_member_of`, `has_permission`, …) | 1.3 |
| 1.5 | RLS de D0 + **suite pgTAP con 6 identidades** | 1.4 |
| 1.6 | Auth UI: registro, login, verificación, recuperación | 1.1 |
| 1.7 | Selector de organización activa + middleware de sesión | 1.5 |
| 1.8 | Gestión de equipo: invitar, asignar roles, revocar | 1.7 |
| 1.9 | `audit_logs` + `domain_events` (outbox) | 0.4 |

> **Punto de control 1:** un usuario puede crear dos organizaciones, alternar entre ellas, invitar a otro usuario, y los tests demuestran que la organización B no ve datos de la A.

### Fase 2 — Datos de referencia y taxonomía (semanas 3–4)

| # | Tarea | Depende de |
|---|---|---|
| 2.1 | `countries`, `currencies`, `fx_rates`, `units_of_measure`, `languages` | 0.4 |
| 2.2 | `admin_divisions` + trigger de `path` + **seed completo de Chile** (16 regiones, 56 provincias, 346 comunas con código CUT) | 2.1 |
| 2.3 | `industries` + traducciones + seed (15 industrias, con desagregación de minería) | 2.1 |
| 2.4 | `taxonomy_nodes` + triggers `path`/`level` + traducciones + sinónimos | 2.1 |
| 2.5 | **Seed de taxonomía**: ~28 categorías raíz del §82, con 2–3 niveles en las 8 prioritarias (transporte, mantenimiento, servicios eléctricos, arriendo de maquinaria, EPP, ingeniería, TI, alimentación/campamentos) | 2.4 |
| 2.6 | `attribute_definitions`, `attribute_options`, `taxonomy_node_attributes` + vista de herencia | 2.4 |
| 2.7 | Seed de atributos para las 8 categorías prioritarias | 2.6 |
| 2.8 | Backoffice de taxonomía, industrias y atributos | 2.6 |

> **Punto de control 2:** un admin crea una categoría nueva con 3 atributos desde la UI y el formulario del proveedor se genera solo, sin deploy.

### Fase 3 — Perfil de proveedor y catálogo (semanas 5–7)

| # | Tarea | Depende de |
|---|---|---|
| 3.1 | `organization_locations`, `organization_contacts`, `organization_media`, `organization_settings` | 1.5, 2.2 |
| 3.2 | Buckets de Storage + policies + upload validado (MIME + magic bytes + tamaño) | 1.5 |
| 3.3 | `organization_industries`, `organization_territories` | 2.2, 2.3 |
| 3.4 | `supplier_offerings` + `offering_taxonomy_nodes` + `offering_industries` | 2.4 |
| 3.5 | `offering_territories`, `offering_pricing`, `offering_media`, `offering_documents` | 3.4 |
| 3.6 | `offering_attribute_values` + validación tipada + formulario dinámico | 2.6, 3.4 |
| 3.7 | `certification_types`, `organization_certifications` | 3.2 |
| 3.8 | `case_studies` + `case_study_taxonomy_nodes` + `client_references` | 3.4 |
| 3.9 | Motor de `completion_pct` de perfil | 3.1–3.8 |
| 3.10 | **Wizard de onboarding proveedor** (8 pasos, guardado parcial) | 3.9 |
| 3.11 | Componentes: `CategorySelector`, `TerritorySelector`, `IndustrySelector`, `AttributeForm`, `ProfileCompletion` | 3.6 |

> **Punto de control 3:** un proveedor real completa su perfil de punta a punta sin ayuda y todo persiste en Postgres.

### Fase 4 — Búsqueda y perfil público (semanas 7–9)

| # | Tarea | Depende de |
|---|---|---|
| 4.1 | `supplier_search_index` + triggers de refresco + job de reconciliación | 3.x |
| 4.2 | Configuración FTS en español: `unaccent`, diccionario, sinónimos, `tsvector` ponderado (A: nombre, B: categoría, C: descripción) | 4.1 |
| 4.3 | `fn_search_suppliers(query, filters, page)` con facetas y conteos | 4.2 |
| 4.4 | Página `/discover` con filtros laterales, chips, ordenamiento, paginación | 4.3 |
| 4.5 | Perfil público `/proveedores/[slug]` con visibilidad graduada | 4.1 |
| 4.6 | SEO: SSG/ISR, sitemap dinámico, JSON-LD, OG images | 4.5 |
| 4.7 | `search_logs`, `search_impressions`, `profile_views`, `offering_views` | 4.3 |
| 4.8 | Comparador de proveedores (hasta 4 lado a lado) | 4.4 |
| 4.9 | `supplier_lists` + `supplier_list_items` (guardar/favoritos) | 4.4 |

> **Punto de control 4:** "transporte de trabajadores Antofagasta minería" devuelve resultados correctos en < 400 ms con 5.000 offerings de prueba.

### Fase 5 — Acreditación (semanas 9–10)

| # | Tarea | Depende de |
|---|---|---|
| 5.1 | `document_types` + seed chileno (F30, F30-1, carpeta tributaria, vigencia, etc.) | 2.1 |
| 5.2 | `organization_documents` + `organization_document_versions` | 3.2 |
| 5.3 | `accreditation_programs`, `requirement_groups`, `accreditation_requirements` + seed del programa base | 5.1 |
| 5.4 | `accreditation_enrollments`, `accreditation_fulfillments`, `section_progress`, `status_history` | 5.3 |
| 5.5 | Triggers de completitud y vigencia | 5.4 |
| 5.6 | UI proveedor: checklist, subida, estado, observaciones | 5.5 |
| 5.7 | Backoffice de revisión: cola, validar/observar/rechazar, historial | 5.5 |
| 5.8 | Job diario de vencimientos + notificaciones escalonadas | 5.5, 1.9 |
| 5.9 | `badge_definitions` + evaluador de reglas + `organization_badges` | 5.5 |
| 5.10 | Notificaciones in-app + email | 1.9 |

> **🚀 CIERRE DE MVP.** Beta cerrada con 20–30 proveedores y 5 compradores reales.

### Fase 6 — Demanda y matching (semanas 11–14)

| # | Tarea |
|---|---|
| 6.1 | `requirements`, `requirement_items`, `requirement_locations`, `requirement_documents` |
| 6.2 | `sourcing_events`, `lots`, `items`, `stages`, `documents` |
| 6.3 | `sourcing_event_criteria` + constructor MUST/NICE |
| 6.4 | `fn_run_matching` etapa 1 (recall) |
| 6.5 | Etapa 2 (elegibilidad + blocking_reasons) |
| 6.6 | Etapa 3 (8 componentes de scoring) |
| 6.7 | Etapa 4 (ranking, modificadores, breakdown) + `match_runs`/`match_results` |
| 6.8 | Suite de 25 casos de oro |
| 6.9 | UI de resultados de matching con explicación y preview de pesos |
| 6.10 | Flujo "RFQ desde búsqueda" (§42) y "RFQ desde necesidad" (§43) |

### Fase 7 — Invitación, Q&A y cotizaciones (semanas 14–18)

| # | Tarea |
|---|---|
| 7.1 | `sourcing_event_invitations` + máquina de estados + historial |
| 7.2 | `sourcing_event_ndas` + `nda_acceptances` |
| 7.3 | Portal del proveedor: bandeja de invitaciones, aceptar/declinar con motivo |
| 7.4 | `sourcing_questions` / `sourcing_answers` con visibilidad |
| 7.5 | `quotations`, `quotation_revisions`, `quotation_items`, `quotation_responses`, `quotation_documents` |
| 7.6 | **RLS de cotizaciones + modo sellado + ceremonia de apertura** ← el bloque más crítico del sistema |
| 7.7 | Formulario de cotización multi-línea con multi-moneda y UF/UTM |
| 7.8 | `conversations`, `messages`, `attachments`, `reads` + Realtime |
| 7.9 | `notifications` + `notification_deliveries` + preferencias |

> **Punto de control 7:** test que demuestra que el Proveedor B **no puede** leer ninguna fila de la oferta del Proveedor A, ni por API ni por Realtime, en ningún estado del evento.

### Fase 8 — Evaluación, negociación y adjudicación (semanas 18–22)

| # | Tarea |
|---|---|
| 8.1 | Comparador horizontal con ponderación configurable |
| 8.2 | `evaluation_templates`, `criteria`, `event_evaluation_setup` |
| 8.3 | `evaluation_assignments` (comité + bloqueo económico) |
| 8.4 | `evaluations` + `evaluation_scores` + consolidación |
| 8.5 | `negotiation_rounds` + nuevas revisiones de cotización |
| 8.6 | `awards`, `award_items`, `award_approvals`, `organization_approval_policies` |
| 8.7 | Notificación a participantes + cierre del evento |
| 8.8 | `buyer_supplier_relationships` (Vendor List) |
| 8.9 | Dashboards de analítica comprador y proveedor |
| 8.10 | `plans`, `plan_entitlements`, `subscriptions`, `usage_counters` |

> **🚀 CIERRE DE V1.**

### Fase 9+ — V2

Acreditación diferenciada → desempeño → Supplier Score → Supplier 360° → contratos → spend analytics → IA → pgvector → pagos → PWA.

---

## M. Riesgos técnicos y deuda potencial

Ordenados por **impacto × probabilidad**.

### 🔴 Críticos

**M1 · Filtración de información comercial confidencial**
*Riesgo:* un proveedor ve la oferta de otro, o el comprador ve ofertas selladas antes de la apertura. En sourcing minero esto termina con la plataforma.
*Mitigación:* RLS como única puerta (nunca filtrado en la UI); suite pgTAP obligatoria con identidad de "proveedor competidor" para cada tabla de la cadena de cotización; canales Realtime con allowlist explícita; auditoría de toda lectura de cotización; revisión de seguridad manual antes de cada release que toque D7.

**M2 · Rendimiento de RLS a escala**
*Riesgo:* policies con subconsultas por fila degradan las consultas dos órdenes de magnitud al pasar de 1.000 a 100.000 filas.
*Mitigación:* `(select auth.uid())` siempre; helpers `SECURITY DEFINER STABLE`; índice en toda columna usada por una policy; benchmark obligatorio con 100k filas sintéticas antes de cerrar cada fase; `EXPLAIN ANALYZE` en CI para las 10 consultas más frecuentes con umbral de regresión.

**M3 · Liquidez del marketplace (riesgo de producto con consecuencia técnica)**
*Riesgo:* RFQ publicadas sin proveedores elegibles. El comprador se va y no vuelve.
*Mitigación técnica:* medir `marketplace_metrics_daily` desde el día 1; alerta cuando una categoría tenga < 3 proveedores elegibles; **bloquear la publicación de una RFQ mostrando "solo hay 1 proveedor elegible, ¿quieres ampliar criterios?"** antes de dejar que el comprador viva la mala experiencia; pre-cargar perfiles desde fuentes públicas con flujo de reclamo (`organization_claims`) para arrancar con densidad.

**M4 · Rendimiento del EAV en búsqueda facetada**
*Riesgo:* filtrar por 6 atributos sobre `offering_attribute_values` genera 6 self-joins y colapsa.
*Mitigación:* el read model con proyección JSONB + GIN es la ruta de lectura, no las tablas EAV; job de conciliación que verifica coherencia; si aun así no escala, materializar columnas dedicadas para los 10 atributos más filtrados de cada categoría top.

### 🟠 Altos

**M5 · Remapeo de taxonomía**
*Riesgo:* reorganizar el árbol en el mes 8 deja 3.000 offerings mal clasificados y rompe los `path` guardados.
*Mitigación:* nunca borrar nodos (`is_active=false` + `merged_into_node_id`); nunca persistir `path` como texto fuera de `taxonomy_nodes` (siempre FK al id); herramienta de remapeo masivo con dry-run en el backoffice; versionar la taxonomía y registrar cada cambio estructural en `audit_logs`.

**M6 · Multi-moneda y unidades de indexación chilenas**
*Riesgo:* contratos en UF, ofertas en USD y CLP comparadas sin conversión coherente producen comparaciones sencillamente falsas. La UF cambia a diario.
*Mitigación:* toda columna de dinero es tripleta `(amount, currency_code, amount_base)` con `fx_rate_snapshot` + `fx_rate_date` congelados al momento del envío; `fx_rates` incluye UF y UTM; el comparador siempre indica la fecha del tipo de cambio usado; jamás recalcular montos históricos con la tasa de hoy.

**M7 · Notificaciones acopladas al modelo**
*Riesgo:* triggers que envían emails desde la base, transacciones que fallan por un webhook caído, imposibilidad de reintentar.
*Mitigación:* patrón outbox estricto — los triggers solo escriben en `domain_events`; un worker procesa, reintenta con backoff y registra en `notification_deliveries`. Agregar WhatsApp o push es agregar un adaptador, no tocar el dominio.

**M8 · Crecimiento sin control de `audit_logs`**
*Riesgo:* auditar todo en una sola tabla la vuelve inmanejable en 12 meses.
*Mitigación:* particionar por mes desde el día 1 (`pg_partman`); definir qué se audita (entidades críticas, no todo); retención declarada (24 meses en caliente, luego archivo).

**M9 · Soft delete inconsistente**
*Riesgo:* `deleted_at` en unas tablas y no en otras, FKs apuntando a filas "borradas", uniques que impiden recrear un slug liberado.
*Mitigación:* lista explícita y cerrada de tablas con soft delete (documentada en `DATABASE.md`); índices únicos parciales `where deleted_at is null`; vistas `v_*_active` como interfaz de lectura por defecto; regla de negocio: no se soft-deletea nada referenciado por un proceso cerrado.

### 🟡 Medios

**M10 · Enums de Postgres rígidos** — quitar un valor de un enum exige recrear el tipo. *Mitigación:* enum solo para conjuntos estables del núcleo (`quotation_status`); tabla catálogo para todo lo que el negocio pueda ampliar. Agregar valores sí es barato; planificar para no tener que quitarlos.

**M11 · Server Actions sin capa de autorización** — RLS protege filas, no operaciones. *Mitigación:* toda Server Action pasa por `policies/` (validación de permiso) + Zod, sin excepción; un lint rule que falle si una acción no invoca `authorize()`.

**M12 · N+1 en listados con jerarquías** — pintar 50 tarjetas resolviendo categorías y territorios una a una. *Mitigación:* el read model trae todo desnormalizado; RPC de Postgres devolviendo JSON agregado para vistas complejas; paginación por cursor (nunca `OFFSET` grande).

**M13 · Storage sin límites reales** — bases de licitación de 500 MB, costos que se disparan. *Mitigación:* cuota por organización según plan (`plan_entitlements`); límites por bucket; compresión de imágenes en el cliente; ciclo de vida a almacenamiento frío en V2.

**M14 · Divergencia del read model** — `supplier_search_index` desincronizado tras un cambio masivo. *Mitigación:* triggers + job nocturno de reconstrucción completa + métrica de divergencia alertada.

**M15 · Testing de negocio insuficiente** — el matching es fácil de romper sin darse cuenta. *Mitigación:* 25 casos de oro versionados; snapshot de `score_breakdown`; el CI falla si un caso cambia sin actualización explícita del snapshot.

**M16 · i18n retrofit** — agregar inglés en el mes 18 con nombres de categoría hardcodeados en español. *Mitigación:* tablas de traducción para catálogos desde el día 1 (aunque solo se pueble `es-CL`); `next-intl` en la UI desde el inicio; nunca texto de negocio en el código.

### 🟢 Bajos pero a vigilar

**M17 · Realtime a escala** — miles de suscripciones concurrentes. Empezar solo con mensajería y notificaciones; medir antes de ampliar.
**M18 · Edge Functions con cold start** — no ponerlas en la ruta crítica de búsqueda; solo trabajos asíncronos.
**M19 · Dependencia de proveedor** — Supabase es Postgres estándar; mantener migraciones portables y evitar features propietarias en el núcleo del dominio.
**M20 · Complejidad del backoffice** — es un producto en sí mismo; presupuestarlo, no tratarlo como "una pantalla más".

---

## Deudas técnicas que se aceptan conscientemente

| Deuda | Por qué se acepta | Cuándo se paga |
|---|---|---|
| Sin PostGIS en MVP; territorio jerárquico y no geométrico | Cubre el 90% de los casos chilenos (la cobertura se declara por comuna) | V2, cuando se pida "radio de 50 km" |
| Revisión de acreditación 100% manual | El volumen inicial lo permite y las reglas aún no están decantadas | V2: validaciones automáticas contra SII y mutualidades |
| Sin pasarela de pago en V1 | Facturación manual con 50 clientes es viable y elimina un frente completo de complejidad | V2 |
| Un solo idioma poblado (es-CL) | Chile primero, pero con el esquema i18n ya montado | Cuando se abra el segundo país |
| Sin API pública | La superficie de API es un compromiso permanente; primero estabilizar el modelo | V3 |
| Búsqueda solo léxica (FTS) | FTS bien configurado con sinónimos resuelve mucho más de lo que se cree | V2 con pgvector |
