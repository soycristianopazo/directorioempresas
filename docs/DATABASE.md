# Base de datos — Estado implementado

> Diseño completo en [02-MODELO-DATOS.md](02-MODELO-DATOS.md).
> Este documento cubre **lo que existe hoy en `backend/alembic/sql/`**.
>
> Nota de stack: el diseño original asumía Supabase Auth (GoTrue) y
> migraciones en `supabase/migrations/`. Esa vía se abandonó — el backend es
> FastAPI + SQLAlchemy async + Alembic, con autenticación propia
> (`users`/`user_sessions`, JWT + bcrypt_sha256) y RLS activado sobre el
> mismo Postgres de Supabase, pero gestionado directamente vía SQL a mano
> (no `supabase db push`, no pgTAP). Ver `backend/alembic/sql/0002_auth_and_rls.sql`
> para el porqué exacto de cada pieza de ese cambio.

---

## Migraciones

| Archivo | Contenido |
|---|---|
| `0001_foundation.sql` | Extensiones (`pgcrypto`, `ltree`, `pg_trgm`, `unaccent`, `citext`), schema `app`, ENUMs raíz, triggers estándar, `slugify`, validación de RUT, rol `app_user` |
| `0002_auth_and_rls.sql` | `users`, `user_sessions`, `user_tokens` (reemplaza `auth.users`/GoTrue), `app.current_user_id()`, `app.is_system_context()` |
| `0003_profiles.sql` | `profiles`, alta desde el servicio de registro (no un trigger sobre `auth.users`) |
| `0004_organizations.sql` | `organizations`, capacidades, roles de negocio, identificadores tributarios |
| `0005_rbac.sql` | `permissions`, `roles`, `role_permissions`, `organization_members`, `member_roles`, `platform_admins`, invitaciones |
| `0006_audit_and_events.sql` | `audit_logs`, `domain_events` (outbox) |
| `0007_rls_helpers.sql` | Funciones helper de RLS (`app.has_permission`, `app.is_member_of`, …) |
| `0008_rls_policies.sql` | Policies del dominio D0 (identidad/tenancy) |
| `0009_seed_roles_permissions.sql` | Catálogo de permisos y roles de sistema (incluye permisos de fases futuras, ver el comentario del archivo) |
| `0010_hardening.sql` | Rol `app_user`: GRANTs, `ENABLE ROW LEVEL SECURITY` en todas las tablas, bypass de sistema, vista `v_my_organizations` |
| `0011_reference_data.sql` | `countries`, `currencies` (incl. UF/UTM), `fx_rates`, `units_of_measure`, `languages` |
| `0012_admin_divisions.sql` | `admin_divisions` + `app.maintain_hierarchy_path()` (trigger genérico de jerarquías, reutilizado por `taxonomy_nodes`/`industries`) |
| `0013_seed_admin_divisions_cl.sql` | 16 regiones + 56 provincias + 346 comunas de Chile. Generado desde `backend/alembic/seed_data/cl_admin_divisions.csv` por `backend/scripts/gen_admin_divisions_sql.py` — no editar a mano |
| `0014_taxonomy_and_industries.sql` | `taxonomy_nodes` (qué se vende) e `industries` (a quién se le vende) — dos árboles ortogonales, ver §D.2 de [01-ARQUITECTURA.md](01-ARQUITECTURA.md) |
| `0015_seed_taxonomy_and_industries.sql` | 28 categorías raíz (8 con 2-3 niveles de profundidad) + 16 industrias |
| `0016_attributes.sql` | `attribute_definitions`, `attribute_options`, `taxonomy_node_attributes`, vista `v_effective_node_attributes` (herencia de atributos por `path`) |
| `0017_seed_attributes.sql` | Atributos de ejemplo para las 8 categorías prioritarias |
| `0018_taxonomy_rls_helpers.sql` | `app.has_platform_permission(perm)` — permisos de plataforma sin organización |
| `0019_taxonomy_rls_policies.sql` | RLS de las tablas de 0011-0016: lectura pública, escritura solo `platform.manage_taxonomy` |
| `0020_organization_profile.sql` | `organization_locations`, `organization_contacts`, `organization_media`, `organization_settings` |
| `0021_organization_industries_territories.sql` | `organization_industries`, `organization_territories` — industrias/cobertura declaradas por la propia empresa |
| `0022_supplier_offerings.sql` | ENUMs de oferta + `supplier_offerings`, `offering_taxonomy_nodes`, `offering_industries`, `offering_territories`, `offering_pricing` — el núcleo del catálogo |
| `0023_offering_media_and_documents.sql` | `offering_media`, `offering_documents` |
| `0024_offering_attribute_values.sql` | `offering_attribute_values`, `offering_attribute_option_values` + trigger `app.validate_offering_attribute_value()` |
| `0025_certifications.sql` | `certification_types` (con seed de 6 tipos) + `organization_certifications` |
| `0026_case_studies.sql` | `client_references`, `case_studies`, `case_study_taxonomy_nodes`, `case_study_media` |
| `0027_completion_pct.sql` | `app.compute_completion_pct(organization_id)` — porcentaje de completitud del perfil |
| `0028_fase3_rls_helpers.sql` | `app.can_view_organization(org)`, `app.can_view_offering(offering)` — helpers de visibilidad reutilizados por ~20 policies |
| `0029_fase3_rls_policies.sql` | RLS de todas las tablas de 0020-0026 |
| `0030_search_index.sql` | `supplier_search_index` — read model desnormalizado de búsqueda (1 fila por oferta), refrescado desde Python, no por trigger |
| `0031_supplier_lists.sql` | `supplier_lists`, `supplier_list_items` — listas de proveedores guardadas por un comprador |
| `0032_analytics.sql` | `search_logs`, `search_impressions`, `profile_views`, `offering_views` — insert-only (salvo el agregado diario de impresiones), sin policy de usuario |
| `0033_fase4_rls.sql` | RLS de las tablas de 0030-0032 |
| `0034_document_repository.sql` | `document_types` (seed chileno: F30, F30-1, carpeta tributaria, vigencia de sociedad, RUT/SII, póliza RC, reglamento interno, accidentabilidad, balance financiero), `organization_documents`, `organization_document_versions` (append-only, reemplaza a la versión activa vía `status`, nunca borra); `organization_certifications.document_version_id` |
| `0035_accreditation_programs.sql` | `accreditation_programs`, `requirement_groups`, `accreditation_requirements`, `accreditation_status_transitions` (seed de las 12 transiciones válidas de la máquina de estados, ver §F.3 de [01-ARQUITECTURA.md](01-ARQUITECTURA.md)) + seed del programa `ACREDITACION_BASE` (4 secciones, 6 exigencias) |
| `0036_accreditation_enrollments.sql` | `accreditation_enrollments`, `accreditation_fulfillments`, `accreditation_section_progress`, `accreditation_status_history` (append-only), `accreditation_review_events` (append-only) |
| `0037_badges.sql` | `badge_definitions` (`rule_expression jsonb`, seed de 3 badges automáticos) + `organization_badges` |
| `0038_fase5_rls.sql` | RLS de las tablas de 0034-0037 |
| `0039_requirements.sql` | `requirements` (la necesidad, §18), `requirement_items`, `requirement_locations`, `requirement_documents` — nunca públicas, privadas de la organización compradora |
| `0040_sourcing_events.sql` | `sourcing_events` (incl. `matching_weights jsonb`, override por evento de los pesos de scoring), `sourcing_event_lots`, `sourcing_event_items`, `sourcing_event_stages`, `sourcing_event_documents`, `sourcing_event_criteria` (MUST_HAVE/NICE_TO_HAVE, 7 tipos con FK real por tipo + CHECK de coherencia, mismo criterio que `accreditation_requirements`) |
| `0041_matching_results.sql` | `match_runs`, `match_results` — append-only (`REVOKE UPDATE, DELETE`), reproducibilidad vía `engine_version` + `weights_snapshot` |
| `0042_search_index_matchable.sql` | `supplier_search_index` gana `is_matchable` (visibilidad graduada PUBLIC/REGISTERED/BUYERS_ONLY para cualquier comprador autenticado — superconjunto de `is_public`, que solo cubre PUBLIC para `anon`) |
| `0043_fase6_rls.sql` | RLS de 0039-0042. Nada de esto es público, ni parcialmente — nunca hay un `select using (true)` ni `can_view_organization(...)` en este archivo |
| `0044_sourcing_event_invitations.sql` | `app.sourcing_invitation_status` (11 estados, tomados de §G.1), `sourcing_event_invitations`, `sourcing_event_invitation_transitions` (transición-como-dato, mismo criterio que `accreditation_status_transitions`), `invitation_status_history` (append-only), `app.has_active_sourcing_invitation()` — cierra un vacío real de fase 6: ningún proveedor invitado podía leer el evento al que fue invitado |
| `0045_sourcing_event_ndas.sql` | `sourcing_event_ndas` (versionado), `nda_acceptances` (append-only — `ip_address`/`user_agent` como en `user_sessions`/`audit_logs`, `accepted_at`/`accepted_by` como en `organization_invitations`, `checksum_sha256` como en `organization_document_versions`) |
| `0046_sourcing_qa.sql` | `sourcing_questions`, `sourcing_answers` (`visibility` `PRIVATE_TO_ASKER`/`ALL_PARTICIPANTS`, anonimiza al autor de cara a otros participantes al publicar, nunca de cara al comprador) |
| `0047_quotations.sql` | `quotations` (contenedor, `supplier_organization_id` propio POR FILA — la pieza que habilita Patrón E en 0049), `quotation_revisions` (append-only, `round_type` con un solo valor usable `'INITIAL'` hoy — `CLARIFICATION`/`COUNTER`/`BAFO` llegan con `ALTER TYPE` cuando exista `negotiation_rounds`, fase 8.5), `quotation_items`, `quotation_responses`, `quotation_documents` |
| `0048_fase7_rls_invitations_qa_ndas.sql` | RLS de invitaciones/NDA/Q&A + policies SELECT adicionales (permisivas, sin tocar 0043) que dan al proveedor invitado visibilidad del evento/lotes/ítems/hitos/criterios/documentos vía `app.has_active_sourcing_invitation()` |
| `0049_fase7_rls_quotations.sql` | RLS de cotizaciones — Patrón E (fila propia, no backstop de permisos). La policy más revisada del proyecto: es el Punto de control 7 del roadmap |
| `0050_conversations.sql` | `conversations` (`context_type` tipado + FKs reales nullable, sin `CONTRACT` — no existe tabla `contracts` todavía, V2), `conversation_participants`, `messages`, `message_attachments`, `message_reads` |
| `0051_notifications.sql` | `notifications`, `notification_preferences`, `notification_deliveries` (canal `EMAIL` stub, sin proveedor decidido — misma desviación de fase 5.10) |
| `0052_fase7_rls_messaging_notifications.sql` | Patrón F (mensajería, por participante) + RLS de notificaciones — ver el gotcha del `RETURNING` en la sección de decisiones de `docs/RLS.md` |
| `0053_sourcing_event_code_seq.sql` | `public.sourcing_event_code_seq` — reemplaza el `count(*)` de `next_event_code()` (fase 6), que era RLS-scoped por organización mientras `event_code` es único a nivel de tabla completa: dos organizaciones distintas creando cada una su primer RFQ del año colisionaban. Bug real de fase 6, encontrado y arreglado durante la verificación de fase 7 — ver `docs/RLS.md` |

Forward-only. **Nunca editar una migración ya aplicada** una vez que corrió contra la base real — se agrega una nueva. (Durante el desarrollo activo de una fase, mientras nada se ha compartido/aplicado en otro entorno, sí se corrige el archivo en el lugar y se reaplica — ver el historial de 0012 como ejemplo real de esto.)

---

## Convenciones

- **PK** `uuid` con `gen_random_uuid()`. Catálogos estables usan su código natural (`permissions.code`, `countries.code`).
- **Timestamps** `created_at` / `updated_at` con trigger `app.set_updated_at()`. `created_at` es inmutable por trigger (`app.prevent_immutable_change()`).
- **Autoría** `created_by` / `updated_by` → `profiles(id)` con `on delete set null`.
- **Soft delete / desactivación**: `organizations` usa `deleted_at`; las jerarquías (`taxonomy_nodes`, `industries`, `admin_divisions`) usan `is_active=false` y **nunca se borran de verdad** — ver §D.5 de [02-MODELO-DATOS.md](02-MODELO-DATOS.md).
- **ENUM** para conjuntos cerrados del núcleo; tabla catálogo para lo que el negocio pueda ampliar sin deploy (ejemplo reciente: `admin_divisions.level_name` es texto libre, no ENUM, porque el vocabulario de niveles varía por país).
- **Jerarquías** (`admin_divisions`, `taxonomy_nodes`, `industries`): self-FK `parent_id` + `level` + `path ltree`, mantenidos por el trigger genérico `app.maintain_hierarchy_path()` (0012). Cualquier cast a `ltree` dentro de una función que no sea `SECURITY DEFINER` debe calificarse `extensions.ltree` explícito — `app_user` no tiene `extensions` en su `search_path` (a diferencia de `postgres`), y un `::ltree` sin calificar falla con "type ltree does not exist", un mensaje que no apunta a la causa real. Ver el comentario extenso en `0012_admin_divisions.sql`.
- **Dinero** siempre `(amount, currency_code)`, con `currencies.decimal_places` gobernando el formateo. UF/UTM se modelan como filas de `currencies` con `is_index_unit=true`, no como un concepto aparte.
- Aplicar convenciones a una tabla nueva: `select app.apply_table_conventions('public.mi_tabla');`

---

## Tablas implementadas

### Identidad (fase 0-1)

**`users`** — Credenciales. Reemplaza `auth.users`: la autenticación la maneja FastAPI con PyJWT + `bcrypt_sha256` (passlib), no GoTrue.

**`profiles`** — 1:1 con `users`, creado por el servicio de registro (no un trigger). `full_name` es columna generada. `last_org_id` es una sugerencia de UI, nunca fuente de autorización. **No tiene `organization_id`**: la pertenencia vive en `organization_members` (§48 del brief).

**`organizations`** — La empresa. Sin campo `type`: ver `organization_capabilities`. `slug` único entre organizaciones vivas.

**`organization_capabilities`** — `BUYER` / `SUPPLIER` / `PLATFORM_ADMIN`. Afectan permisos y navegación.

**`organization_legal_identifiers`** — Multi-país. El RUT chileno se valida por módulo 11 con un `CHECK` que llama a `app.is_valid_rut()`.

### RBAC (fase 0-1)

**`permissions`** — Permisos atómicos con formato `recurso.acción`, incluidos varios de fases futuras (sembrados de antemano para que el catálogo sea estable — ver el comentario de `0009`).
**Regla:** el código nunca compara nombres de rol. Chequea `has_permission(org, 'organization.update')`.

**`roles`** — Roles de sistema (plataforma + organización). `organization_id is null` → rol de sistema.

**`platform_admins`** — Roles de plataforma, separados de la membresía de empresa. `(user_id, role_id)` como PK; ver `app.has_platform_permission()` (0018) para el chequeo granular por permiso, no solo por rol.

**`organization_invitations`** — Se almacena solo el hash del token.

### Referencia y taxonomía (fase 2)

**`countries` / `currencies` / `fx_rates` / `units_of_measure` / `languages`** — Catálogos pequeños, lectura pública. `fx_rates` solo tiene filas de ejemplo hoy: la ingesta diaria real es trabajo de una fase posterior.

**`admin_divisions`** — Jerarquía territorial genérica multi-país. `level_name` es texto libre a propósito. Sembrada para Chile (16 regiones/56 provincias/346 comunas) desde el CUT oficial (SUBDERE).

**`taxonomy_nodes`** — Árbol de QUÉ se vende (transporte, mantención, EPP, …). `node_type ∈ {CATEGORY, SUBCATEGORY, SPECIALTY, SERVICE, PRODUCT}`. `is_leaf` lo mantiene un trigger, no se setea a mano.

**`industries`** — Árbol de A QUIÉN se le vende (minería, construcción, …). Independiente de `taxonomy_nodes` por diseño — ver §D.2 de [01-ARQUITECTURA.md](01-ARQUITECTURA.md) para por qué un solo árbol con la industria como raíz duplicaría cada rama de oferta N veces.

**`attribute_definitions` / `attribute_options` / `taxonomy_node_attributes`** — EAV tipado. `taxonomy_node_attributes.is_inherited=true` propaga el atributo a todos los descendientes del nodo — resuelto por la vista `v_effective_node_attributes` (herencia por `path`, la definición más específica gana sobre la heredada).

### Perfil extendido y catálogo de oferta (fase 3)

**`organization_locations` / `organization_contacts`**  — Sedes y contactos de la empresa. Desactivación vía `is_active=false`, no `DELETE` real (mismo criterio que las jerarquías, aunque estas no son datos de gobernanza append-only — es simplemente para no romper referencias históricas).

**`organization_media`** — Logo/banner de la organización. `LOGO`/`BANNER` son singleton por organización: subir uno nuevo reemplaza el anterior (borra la fila y el objeto de Storage previos).

**`organization_settings`** — Fila 1:1 creada automáticamente por `services.organizations.create_organization()` al dar de alta la empresa, no por trigger.

**`organization_industries` / `organization_territories`** — Industrias que la empresa dice atender y cobertura territorial que declara, independientes de la taxonomía/industrias de plataforma (fase 2) pero referenciándolas por FK.

**`supplier_offerings`** — El producto/servicio en sí. `status ∈ {DRAFT, ACTIVE, PAUSED, ARCHIVED}`; la transición DRAFT→ACTIVE (`publish_offering`) exige `short_description` y al menos un nodo de taxonomía asignado, validado en `services/offerings.py`, no en un CHECK de SQL.

**`offering_taxonomy_nodes` / `offering_industries` / `offering_territories`** — Clasificación por oferta: QUÉ es (taxonomía) y A QUIÉN sirve (industria), reutilizando la misma clasificación dual-eje de fase 2 pero a nivel de oferta individual en lugar de organización completa. `offering_taxonomy_nodes.is_primary` determina qué nodo gobierna los atributos dinámicos efectivos de esa oferta.

**`offering_pricing`** — 1:1 con la oferta. `price_type ∈ {FIXED, FROM, RANGE, ON_REQUEST}`; dinero siempre `(amount, currency_code)` según la convención general.

**`offering_media` / `offering_documents`** — Fotos (bucket público `org-media`) y fichas técnicas PDF (bucket privado `org-documents`, servido vía URL firmada de 1 hora). Relación pura, sin gobernanza append-only: `DELETE` real al quitar una foto o documento.

**`offering_attribute_values` / `offering_attribute_option_values`** — EAV tipado por oferta, valores contra las `attribute_definitions` de fase 2 heredadas por su nodo de taxonomía primario. Un CHECK (`num_nonnulls`) exige que a lo más un slot de valor esté poblado; el trigger `app.validate_offering_attribute_value()` valida además que el slot poblado coincida con el `data_type` de la definición — algo que un CHECK plano no puede expresar porque necesita un JOIN.

**`certification_types`** (catálogo, seed de 6) **/ `organization_certifications`** — Certificaciones autodeclaradas por la empresa (NCh, ISO, OS10, …). Sin repositorio de documentos versionado todavía: eso es la acreditación completa de una fase posterior — aquí solo se guarda el dato declarado (`certificate_number`, fechas, `verification_status` por defecto sin verificar).

**`client_references` / `case_studies` / `case_study_taxonomy_nodes` / `case_study_media`** — Historial comercial autodeclarado: a quién le han vendido y casos de éxito concretos, con fotos y etiquetado de taxonomía propio (sin `is_primary`, a diferencia de `offering_taxonomy_nodes` — un caso de éxito puede tocar varias categorías por igual).

**`app.compute_completion_pct(organization_id)`** — No es una tabla sino una función que resume cuánto del perfil está lleno; se invoca desde `services/completion.py::recompute_completion_pct()` tras cualquier mutación relevante (perfil, catálogo, credenciales) y escribe el resultado en `organizations.completion_pct`. Requiere un `flush()` explícito antes de leer vía SQL crudo en la misma transacción — `SessionLocal` corre con `autoflush=False` en todo el proyecto (`backend/app/db/session.py`), así que una mutación ORM pendiente no es visible todavía para una consulta `text()` en la misma sesión sin ese flush.

### Búsqueda y descubrimiento público (fase 4)

**`supplier_search_index`** — Read model desnormalizado, 1 fila por oferta: `search_vector tsvector` (FTS en español, `to_tsvector('spanish', extensions.unaccent(...))`, ponderado A=nombre/B=categoría+sinónimos+industria/C=descripción larga/D=nombre de la empresa), arrays `taxonomy_node_ids`/`industry_ids`/`admin_division_ids` para filtrado facetado (`&&`), `attributes jsonb` (proyección de `offering_attribute_values` filtrada a `is_filterable=true`), `is_public` precalculado (offering+organización ACTIVE y visibility=PUBLIC — exactamente lo que ve un visitante sin sesión) y `completion_pct` desnormalizado como proxy de calidad. **No se refresca por trigger**: `services/search.py::reindex_offering()` lo recalcula en la MISMA transacción que la mutación que lo dispara (llamado desde `services/offerings.py` en cada cambio de oferta/taxonomía/precio/atributos, y desde `services/organizations.py` cuando cambia `visibility`/`status`) — mismo criterio que `recompute_completion_pct`, incluido el `flush()` previo por el mismo motivo de `autoflush=False`. Sin columnas de `is_accredited`/`supplier_score`: esos son conceptos de fase 5/6 que todavía no existen: el orden por defecto es `ts_rank` + `completion_pct`. `backend/scripts/reindex_search.py` reconstruye el índice completo a mano — no hay scheduler/cron en este stack, es un script de reconciliación de uso manual.

**`supplier_lists` / `supplier_list_items`** — Listas de proveedores guardadas por un comprador (favoritos). Reutiliza los permisos `vendor_list.read`/`vendor_list.manage`, ya sembrados en `0009` para esta fase exacta.

**`search_logs` / `search_impressions` / `profile_views` / `offering_views`** — Analítica de búsqueda y visitas. Insert-only salvo `search_impressions` (agregado diario, incrementado por upsert) — `search_logs`/`profile_views`/`offering_views` tienen `REVOKE UPDATE, DELETE` para `app_user`, mismo criterio que `audit_logs`. Escritas siempre en `session_for_system()`: el visitante anónimo que dispara estos inserts no tiene permiso propio para escribir, el sistema registra en su nombre.

Las páginas públicas indexables (`/discover`, `/proveedores/{slug}`, servidas por FastAPI+Jinja2 fuera de `/api` — ver `backend/app/api/public.py`) y la API JSON equivalente para la SPA de comprador (`/api/discover/*`) comparten exactamente la misma lógica de `services/search.py`; RLS decide qué es visible según quién pregunta (anónimo o autenticado), no hay chequeo de permiso adicional en Python para estas lecturas públicas.

### Observabilidad

**`audit_logs`** — Inmutable: `REVOKE UPDATE, DELETE` para `app_user`.

**`domain_events`** — Outbox transaccional. Sin consumidor todavía (llega en una fase posterior).

### Invitación, cotizaciones y colaboración (fase 7)

**`sourcing_event_invitations` / `invitation_status_history`** — Máquina de 11 estados (`INVITED → VIEWED → NDA_ACCEPTED → INTERESTED → PARTICIPATING → QUOTED`, más `DECLINED`/`NO_RESPONSE`/`WITHDRAWN`/`DISQUALIFIED`/`EXPIRED`) tomada de §G.1, recortada a lo que esta fase puede alcanzar por sí sola — `SHORTLISTED`/`NEGOTIATING`/`AWARDED`/`NOT_AWARDED` del diagrama original dependen de evaluación/adjudicación (fase 8, no existe la infraestructura). `services/invitations.py::_transition()` valida cada cambio contra `sourcing_event_invitation_transitions` antes de aplicarlo, mismo patrón que `accreditation.py`.

**`sourcing_event_ndas` / `nda_acceptances`** — Versionado + aceptación con IP/hash, append-only. `services/invitations.py::accept_nda()` transiciona la invitación a `NDA_ACCEPTED` en la misma llamada.

**`sourcing_questions` / `sourcing_answers`** — Q&A del evento. `sourcing_questions.is_answered` se mantiene por el service al insertar la respuesta, no por trigger. `visibility=ALL_PARTICIPANTS` anonimiza al autor frente a otros participantes cuando se publica (`published_at`), nunca frente al comprador.

**`quotations` / `quotation_revisions` / `quotation_items` / `quotation_responses` / `quotation_documents`** — El bloque más sensible del proyecto (§G.3, Punto de control 7). `quotations` es el contenedor, sin montos, con `supplier_organization_id` propio por fila — la pieza que hace posible que RLS distinga Proveedor A de Proveedor B en la misma tabla (Patrón E, ver `docs/RLS.md`). `quotation_revisions` es append-only de verdad: cada envío es una fila nueva (`round_number` incremental), nunca se corrige una ya enviada — se permite reenviar antes del deadline, la sellabilidad no depende de eso. `quotations.current_revision_id` es el puntero autoritativo a la vigente, actualizado por `services/quotations.py::submit_revision()` en la misma transacción del INSERT; `quotation_revisions.is_current` es documental, nunca se lee para decidir cuál es la vigente.

**`conversations` / `conversation_participants` / `messages` / `message_attachments` / `message_reads`** — Mensajería con contexto tipado. Actualizaciones en vivo por **polling** (`GET .../messages?after=<cursor>`), no Supabase Realtime — el frontend de este proyecto no tiene ninguna dependencia de Supabase (confirmado por grep completo), y Realtime necesitaría una identidad reconocida por Supabase Auth que este proyecto deliberadamente no emite (mismo motivo por el que se abandonaron GoTrue/PostgREST, ver nota de stack al inicio de este documento).

**`notifications` / `notification_preferences` / `notification_deliveries`** — In-app únicamente en esta fase (`EMAIL` stub). Sin `domain_events` de por medio: sería el primer productor Y primer consumidor de ese outbox a la vez, construir el mecanismo completo para un solo caso de uso es la abstracción prematura que este proyecto evita — `services/notifications.py::notify_user()`/`notify_org()` escriben directo desde el service que dispara el evento de negocio, en un `session_for_system()` corto.

### Evaluación, negociación, adjudicación, AVL, analítica y facturación (fase 8) — cierre de V1

**`evaluation_templates` / `evaluation_criteria` / `event_evaluation_setup`** — Plantillas reutilizables a nivel de organización; `event_evaluation_setup` congela un snapshot (`criteria_snapshot` jsonb) al aplicar una plantilla a un evento, mismo criterio que `match_runs.weights_snapshot` (fase 6) — editar la plantilla después no altera un proceso ya configurado. A diferencia de `match_runs`, esta fila **sí es mutable** (una por evento) mientras no exista ninguna evaluación `SUBMITTED` — `services/evaluations.py` bloquea el re-setup una vez que el comité empezó a evaluar.

**`evaluation_assignments` / `evaluations` / `evaluation_scores`** — El comité (`organization_member_id` × `dimension` × `can_view_commercial`) es puramente declarativo: la fila NO otorga acceso a datos de cotización por sí sola. `evaluations`/`evaluation_scores` son mutables mientras `status='DRAFT'`, congeladas de facto al pasar a `SUBMITTED`.

**Bloqueo económico (§H, la decisión de diseño más importante de esta fase)** — Postgres RLS es estrictamente a nivel de fila, nunca de columna, así que "el evaluador técnico nunca ve montos" no se resuelve con una policy nueva sobre `quotation_items`/`quotation_revisions` (daría la fila entera o nada) — y `EVALUATOR` no tiene `quotation.read`, así que el Patrón E de `0049` (fase 7, sin tocar) rechazaría a cualquier evaluador de plano. Solución: 4 funciones `SECURITY DEFINER STABLE` en `0057_evaluation_economic_lock_functions.sql` (`app.list_quotation_items_for_technical_evaluation`, `_responses_`, `_documents_for_technical_evaluation`, `_revisions_for_commercial_evaluation`), cada una con proyección explícita de columnas — las 3 técnicas **nunca** seleccionan `unit_price`/`discount_pct`/`tax_rate`/`line_total`/montos; la comercial exige `can_view_commercial=true` **y** reutiliza la misma regla de apertura de sobre de `0049` (`bid_mode='OPEN' or bid_opened_at is not null`) dentro de su propio cuerpo. `repositories/evaluations.py` las invoca vía `text()`, nunca `select(QuotationItem)` directo. Verificado en vivo (no solo en tests): la respuesta JSON de `GET .../evaluations/mine` para un evaluador técnico no contiene ninguna clave de precio, en ningún nivel del payload.

**`quotation_comparisons`** — Append-only (mismo criterio que `match_runs`), una fila por corrida del comparador ponderado con su propio `criteria_snapshot` + `ranking` (jsonb). `services/evaluations.py::run_comparator()` agrega `evaluation_scores` de evaluaciones `SUBMITTED`, pondera por `evaluation_criteria.weight`. Bug real encontrado en vivo: los valores UUID de `supplier_organization_id` dentro del dict de `ranking` deben convertirse a `str()` antes de insertar en la columna `jsonb` — un UUID crudo hace fallar la serialización JSON de SQLAlchemy (`TypeError: Object of type UUID is not JSON serializable`), silencioso hasta que se corre contra datos reales.

**`negotiation_rounds` / `negotiation_round_participants`** — Solo `round_type in ('COUNTER','BAFO')` — `CLARIFICATION` se agregó al enum `app.quotation_round_type` (fase 8.5, `0059`) pero deliberadamente no tiene tabla propia: una aclaración no cambia el monto ni genera `quotation_revision`, así que reutiliza la mensajería de fase 7 (`conversations`) tal cual. `services/quotations.py::submit_revision()` ahora acepta `round_type` parametrizable (antes hardcodeado a `'INITIAL'`) para que `services/negotiations.py::submit_counter()` reutilice el mismo flujo de envío sin duplicarlo.

**Bug real de recursión de RLS (`0074`)** — `0061_fase8_rls_negotiation.sql` definió un ciclo: la policy de `negotiation_rounds` consultaba `negotiation_round_participants` con un `EXISTS` directo, y la de `negotiation_round_participants` consultaba `negotiation_rounds` de vuelta — "infinite recursion detected in policy for relation negotiation_round_participants", encontrado por la suite de tests (no por el dry-run de migraciones, que no ejercita RLS real). Mismo bug de clase que `conversation_participants` en fase 7 (`0052`) y mismo fix: una función `SECURITY DEFINER STABLE` (`app.is_negotiation_round_participant()`) rompe el ciclo porque su consulta interna corre como dueño de la función, sin volver a evaluar la policy que la llama.

**`awards` / `award_items` / `award_approvals` / `organization_approval_policies`** — Mecanismo de aprobación de dos capas: `organization_approval_policies` decide cuántos pasos hacen falta y qué rol requiere cada uno según el monto (`amount_base`, en la moneda base del evento); `organization_members.approval_limit_amount` (columna que **ya existía desde fase 1**, `0005_rbac.sql` — fase 8 es la primera en usarla) decide qué miembro concreto resuelve cada paso — el de menor límite que igual alcanza el monto, no siempre el de mayor jerarquía. Si cero políticas aplican, el award queda `APPROVED` de inmediato. `award_approvals` tiene autoservicio estricto en RLS: nadie decide el paso de otro aunque tenga `award.approve` a nivel de organización — el permiso abre la cola de lectura, no la escritura de una fila ajena.

**`buyer_supplier_relationships` / `buyer_supplier_notes`** — Vendor List / AVL, ciclo de vida real (`POTENTIAL/IN_EVALUATION/APPROVED/CONDITIONAL/SUSPENDED/BLOCKED`), genuinamente distinta de `supplier_lists` (fase 4, favoritos sin semántica de relación). Cierra el TODO explícito que `services/matching.py::compute_accreditation_fit()` dejó documentado desde fase 6: `AVL='APPROVED'` da el fit máximo (prioridad sobre acreditación de programa), `BLOCKED` excluye directamente en Recall (Etapa 1) antes de llegar a scoring — elegibilidad y puntaje son cosas distintas, mismo criterio que un MUST_HAVE bloqueante.

**`marketplace_metrics_daily`** — Agregados diarios (ayer hacia atrás); el día corriente se calcula en vivo en `services/analytics.py` porque esperar al script manual (`scripts/aggregate_marketplace_metrics.py`, sin scheduler real — mismo criterio que `reindex_search.py`) sería más caro que un par de queries directas. `dimension_id` es una FK polimórfica sin constraint (su tabla depende de `dimension`) — la integridad la garantiza el único escritor real (el script, en `session_for_system()`).

**`plans` / `plan_entitlements` / `subscriptions` / `usage_counters` / `billing_events`** — Sin pasarela de pago en V1 (facturación manual, desviación ya documentada). `plans`/`plan_entitlements` sembrados como migración de datos (`0073`, mismo criterio que la semilla `ACREDITACION_BASE`), catálogo público de lectura. `services/entitlements.py::assert_entitlement()` trata la ausencia de `subscriptions` como plan `FREE` implícito (una organización recién creada no debe bloquearse por no tener fila todavía) y hace fail-open si la feature no está modelada en `plan_entitlements` — RBAC decide SI el usuario puede intentar la acción, este módulo decide si la ORGANIZACIÓN ya se quedó sin cupo, son chequeos independientes. Bug de secuencia real encontrado en vivo con `seed.py`: las suscripciones deben asignarse **antes** de invitar al equipo — el plan `FREE` limita `team.member` a 3 invitaciones totales, y una organización que recién se está armando (varias invitaciones antes de tener plan pago) choca con su propio límite.

**Otros dos bugs reales de `on delete cascade` faltante, encontrados en vivo corriendo `seed.py` (no en tests, que nunca ejercitan `wipe_existing()` dos veces seguidas)**: `conversations.created_by_organization_id`/`conversations.organization_id`/`messages.sender_organization_id` (todas de fase 7, `0050`) referenciaban `organizations` sin cascada — cualquier conversación real creada en el navegador dejaba a `wipe_existing()` incapaz de borrar la organización de prueba. Corregido en `0075`/`0076`.

### Acreditación diferenciada y homologación cruzada (fase 9)

**`accreditation_program_equivalences`** (`0077`) — Tabla nueva, no columna: "estar `ACCREDITED` en `accepted_program_id` también satisface `program_id`, con score 0.90 (nunca 1.00, reservado a la acreditación directa)" — la rama que `docs/03-MATCHING-ENGINE.md` §H.4.5 documentaba sin implementar desde fase 6 ("acreditado en un programa de nivel superior o equivalente → 0.90"). Dirigida y unilateral a propósito: el dueño de `program_id` decide qué acepta, sin necesitar consentimiento del otro programa; homologar en ambos sentidos requiere dos filas. No es append-only (a diferencia de `accreditation_status_history`) — es una decisión de configuración del dueño del programa, revocable, mismo criterio que `requirement_groups`/`accreditation_requirements`.

**`app.can_write_accreditation_program()`** (`0078`) — Centraliza la condición de escritura de `accreditation_programs`/`requirement_groups`/`accreditation_requirements`, repetida 3 veces en `0038_fase5_rls.sql`, para reutilizarla en la policy de `accreditation_program_equivalences` sin repetir el `EXISTS` a mano.

**`app.is_own_program_reviewer()`** (`0079`) — Fase 5 dejó las columnas `owner_scope`/`owner_organization_id` listas para "programa propio de un comprador" pero con la UI de autoría deferida (comentario literal en `0035`). Fase 9 la construye: un comprador con `accreditation.manage` sobre SU organización revisa (`decide_enrollment`/`review_fulfillment`/cola propia) los enrollments de SUS programas `owner_scope=ORGANIZATION` — nunca los de otro comprador, aunque tenga `accreditation.manage` en su propia organización, y nunca los programas `owner_scope=PLATFORM` (esos siguen siendo del revisor de plataforma exclusivamente). `organization_documents`/`organization_document_versions` ganan la misma rama SOLO en SELECT y acotada al documento específico enviado como evidencia de un fulfillment de SU programa (`app.is_own_program_reviewer_for_document[_version]`) — a propósito más estricta que el precedente de `platform.review_accreditation`, que da lectura a TODOS los documentos de TODAS las organizaciones sin acotar a fulfillments reales: un comprador es una contraparte de negocio, no un empleado neutral de plataforma.

**`accreditation.manage` reactivado** (`0080`) — Sembrado desde fase 5 (`0009`) pero sin rol asignado hasta ahora (`ORG_OWNER` ya lo tenía gratis vía su comodín `*`). Fase 9 lo asigna a `BUYER_MANAGER`/`PROCUREMENT_ANALYST` — mismo perfil que ya administra `vendor_list.manage`. Pasa a significar, de forma unificada, administrar programas propios (crear/editar programa, secciones, exigencias, equivalencias) Y revisar sus enrollments — sin un permiso separado `accreditation.review_own`, que sería una distinción sin diferencia real.

**Bug real de RLS encontrado en vivo corriendo `seed.py` (no en el dry-run de migraciones) — dos guardas independientes dejaron de estar de acuerdo (`0081`)**: `services/accreditation.py::_require_program_writer()` chequeaba `accreditation.manage` correctamente desde el principio, pero la policy `accreditation_programs_write` (heredada de fase 5, `0038`) seguía exigiendo únicamente `organization.update` para la rama `owner_scope=ORGANIZATION` — el único permiso que existía cuando esa policy se escribió. Un `BUYER_MANAGER` con `accreditation.manage` pasaba el chequeo de Python y reventaba en el `INSERT` real (`"new row violates row-level security policy for table accreditation_programs"`). Fix: la rama `ORGANIZATION` acepta `organization.update` **o** `accreditation.manage` — ver el detalle completo en `docs/RLS.md`.

**Extensión de alcance en el motor de matching, no solo en el esquema de acreditación** — la homologación cruzada tenía que resolverse en los DOS caminos independientes por los que un evento exige acreditación: `sourcing_events.requires_accreditation_program_id` (alimenta el score `accreditation_fit`, vía `matching_repo.fetch_equivalent_accreditation_status()` nuevo, hermano de `fetch_accreditation_status`) y `sourcing_event_criteria` con `criterion_type='ACCREDITATION'` + `is_blocking=true` (alimenta la elegibilidad DURA de Etapa 2, `repositories/matching.py::_ELIGIBLE_BY_CRITERION_SQL["ACCREDITATION"]`). Sin tocar el segundo camino, un comprador que exige acreditación como MUST_HAVE bloqueante — el uso más estricto, y probablemente el más común en compradores serios — excluiría a un proveedor homologado ANTES de llegar al scoring, dejando la homologación cruzada silenciosamente no funcional para ese caso.

**Fix de seguridad real, no solo de fase 9**: `sourcing_events.requires_accreditation_program_id`/`sourcing_event_criteria.accreditation_program_id` eran FKs completamente libres desde fase 6 — cualquier comprador podía exigir el programa PRIVADO (`owner_scope=ORGANIZATION`) de OTRO comprador al crear un evento o un criterio, sin ninguna validación. El hueco era preexistente pero nunca explotable hasta que fase 9 permitió crear programas `ORGANIZATION` de verdad. `services/sourcing.py::_validate_accreditation_program()` lo cierra en `create_event`/`update_event`/`add_criterion`.

---

## Capa de aplicación (no son funciones SQL invocables)

A diferencia del diseño original (RPCs plpgsql expuestos vía PostgREST), la
lógica de negocio vive en `backend/app/services/*.py` — funciones Python que
abren su propia transacción (`session_for_user`/`session_for_system` de
`backend/app/db/rls.py`) y orquestan repositorios. Las piezas equivalentes a
los RPCs de antes:

| Servicio | Qué hace |
|---|---|
| `auth.register` / `auth.login` | Alta de usuario + perfil; emisión de tokens |
| `organizations.create_organization` | Organización + capacidades + RUT + membresía + rol de dueño, en una transacción |
| `team.invite_member` / `team.accept_invitation` | Invitaciones por hash de token |
| `taxonomy.create_taxonomy_node` / `create_industry` / `create_attribute_definition` / `link_attribute_to_node` | Administración de taxonomía — exige `platform.manage_taxonomy`, verificado con `app.has_platform_permission()` **antes** de mutar |
| `organization_profile.*` | Ubicaciones, contactos, media, industrias/territorios de la empresa |
| `offerings.*` | CRUD del catálogo — `offering.write`/`offering.publish`/`offering.delete` distinguidos por acción específica, no solo por RLS |
| `credentials.*` | Certificaciones, referencias de clientes, casos de éxito |
| `completion.recompute_completion_pct` | Recalcula y persiste `organizations.completion_pct` tras cualquier mutación de perfil/catálogo/credenciales; además actualiza el `completion_pct` denormalizado en `supplier_search_index` |
| `search.reindex_offering` / `reindex_org_offerings` | Recalcula `supplier_search_index`, llamado desde `offerings.py`/`organizations.py` tras cada mutación relevante |
| `search.search_offerings` / `get_public_organization` | Búsqueda facetada y perfil público de organización — consumidos por `app/api/public.py` (Jinja2) y `/api/discover/*` (JSON, SPA) |
| `supplier_lists.*` | CRUD de listas de proveedores guardadas (`vendor_list.read`/`vendor_list.manage`) |
| `documents.*` | Repositorio de evidencia — subida versionada a `org-documents`, validación por magic bytes (`app.core.file_validation`), permisos `document.read`/`write`/`delete` |
| `accreditation.enroll` / `submit_evidence` / `submit_for_review` / `respond_to_observation` | Lado proveedor de la postulación — cada transición de estado se valida contra `accreditation_status_transitions` (dato, no código) antes de aplicarse |
| `accreditation.review_fulfillment` / `decide_enrollment` | Lado revisor (`platform.review_accreditation`, vía `app.has_platform_permission()` — NO `app.has_permission()`, porque un revisor de plataforma no pertenece a la organización postulante) |
| `accreditation._recompute_completion` | Fórmula de completitud (§F.4): `Σ(requirement.weight × fulfillment_factor) / Σ requirement.weight`, global y por sección, recalculada en la misma transacción tras cada mutación relevante — mismo patrón que `completion.recompute_completion_pct`. La vigencia (`expires_at >= current_date`) se evalúa en la propia consulta, no depende de un job — sin fase 5.8 (job diario), un ítem `APPROVED` pero vencido pierde su crédito de completitud al leer, aunque su `status` guardado no cambie hasta que algo lo toque |
| `badges.evaluate_badges_for_org` | Evaluador determinístico de `badge_definitions.rule_expression` (`{"all": [{"fact", "op", "value"}]}`) — nunca reglas hardcodeadas en Python; llamado desde `accreditation.decide_enrollment` en la misma transacción |
| `requirements.*` / `sourcing.*` | CRUD de la necesidad y del proceso de sourcing (`requirement.read`/`write`, `sourcing_event.read`/`create`/`publish`/`cancel`) |
| `matching.run_matching` | El motor (§H, docs/03-MATCHING-ENGINE.md): Etapas 1-2 (recall + elegibilidad) en SQL vía `repositories/matching.py` — trabajo de conjuntos sobre hasta ~500 candidatos; Etapas 3-4 (scoring + ranking) en Python puro (`compute_category_fit`, `compute_capacity_fit`, etc. — sin DB, testeadas en `tests/test_matching_scoring.py`), sobre el conjunto ya filtrado. `dry_run=True` reusa el recall/elegibilidad ya calculado y solo re-corre scoring con pesos distintos, sin persistir — el preview de §H.7 sin pagar el costo de Etapa 1-2 en cada ajuste de slider |
| `invitations.*` | Invitación y NDA (fase 7.1/7.2) — `_transition()` valida contra `sourcing_event_invitation_transitions` antes de aplicar; `mark_quoted()` es la única función pensada para llamarse desde OTRO service (`quotations.py`) dentro de una transacción ya abierta |
| `qa.*` | Preguntas y respuestas (fase 7.4) — RLS ya filtra qué preguntas ve cada quién, el service no vuelve a filtrar en lectura; `publish_answer()` es idempotente (no renotifica en publicaciones repetidas) |
| `quotations.*` | Contenedor + envío de revisiones + ceremonia de apertura (fase 7.5/7.6/7.7) — `submit_revision()` llama a `fx.to_base_amount()` antes de insertar y a `invitations.mark_quoted()` en la misma transacción |
| `fx.get_latest_rate` / `fx.to_base_amount` | Primer consumidor real de `fx_rates` (existía desde `0011`, sin consumidor hasta esta fase) — convierte cada `quotation_revisions.total_amount` a la moneda del propio evento, con la tasa más reciente `valid_on <= fecha de envío` |
| `messaging.*` | Conversaciones con contexto tipado (fase 7.8) — `list_messages(after=...)` es el contrato de polling que consume el frontend, sin websockets |
| `notifications.notify_user` / `notify_org` | Escritura directa a `notifications` desde otros services (invitación enviada, pregunta respondida, cotización recibida, ofertas abiertas), vía `session_for_system()` — contrato público reutilizado por `invitations.py`/`qa.py`/`quotations.py` |

**Gotchas reales de fase 7, encontrados en verificación manual en el navegador (ningún test los atrapó — quedan documentados para no repetirlos):**

- **Choque de rutas real**: `app/api/v1/team.py` ya tenía `GET /organizations/{id}/invitations` (invitaciones de MIEMBROS DE EQUIPO) antes de que fase 7 agregara `GET /organizations/{id}/invitations` para la bandeja del PROVEEDOR — mismo path exacto, dos recursos distintos. FastAPI empareja por orden de montaje en `main.py`; `team_router` gana silenciosamente, sin error, y la ruta nueva queda inalcanzable. Renombrado a `/organizations/{id}/sourcing-invitations`. Antes de reutilizar un patrón de path (`/organizations/{id}/<recurso>`) en una fase nueva, `grep` el path exacto contra todos los routers ya montados.
- **`services/sourcing.py::get_event_detail()` era estrictamente del comprador** (`event.organization_id == organization_id`, más `sourcing_event.read` de ESA organización) — correcto en fase 6, cuando nadie más que el comprador podía leer un evento. Fase 7 le dio a RLS una rama adicional para el proveedor invitado (`has_active_sourcing_invitation`, `0048`), pero el chequeo de Python de este endpoint específico no se actualizó — seguía rechazando con 404 a un proveedor con invitación real. Corregido: la comparación de dueño solo aplica (y solo entonces se exige el permiso) cuando `organization_id` coincide con la del evento; si no coincide, la única pregunta es si `get_event` (RLS-scoped) devolvió una fila — si la devolvió, es porque RLS ya decidió que este usuario puede verla por la otra rama. Lección: cuando RLS gana una rama de acceso nueva para un rol distinto, hay que revisar TODOS los checks de permiso en Python que leen esa misma tabla, no solo agregar la policy.

Todas ellas verifican el permiso ANTES de mutar (no dejan que RLS bloquee el
`UPDATE`/`INSERT` y lo detecten por sus efectos) — ver el comentario en
`backend/app/repositories/organizations.py::has_permission` para el porqué
exacto (evita un `StaleDataError` de SQLAlchemy).

---

## Entorno de desarrollo

Sin Docker, sin CLI de Supabase — conexión directa al proyecto hospedado.

```bash
# Aplicar migraciones (rol postgres, vía el pooler de sesión)
cd backend && source .venv/bin/activate && alembic upgrade head

# Verificar en limpio antes de aplicar contra la base real
node scripts/db-dryrun-migrations.mjs

# Rotar la contraseña de app_user y escribir backend/.env
node scripts/db-setup-app-role.mjs

# Datos de prueba (reutiliza los servicios de la aplicación, no INSERTs a mano)
cd backend && python seed.py

# Crear los buckets de Supabase Storage (idempotente)
node scripts/storage-setup-buckets.mjs

# Reconstruir el índice de búsqueda completo (reconciliación manual, fase 4)
cd backend && PYTHONPATH=. python scripts/reindex_search.py

# Tests de integración (contra la misma base real — no hay base de test aparte)
cd backend && source .venv/bin/activate && python -m pytest tests/ -v
```

**Tests de integración** (`backend/tests/`): corren contra la base real de
desarrollo, ejercitando la capa de servicio directamente (sin HTTP) con datos
desechables por test (`conftest.py`: usuario/organización/programa con sufijo
aleatorio, borrados al terminar). Cubren lo que la verificación manual no
atrapa de forma confiable entre fases: la fórmula de completitud (§F.4) y el
límite de permiso proveedor/revisor (`app.has_permission` vs
`app.has_platform_permission` — la confusión de estos dos costó un bug real en
fase 5). `pytest.ini` fija `asyncio_default_fixture_loop_scope = session`:
el engine de SQLAlchemy es un singleton de módulo (`app/db/session.py`) con
su propio pool de conexiones asyncpg, y el scope de loop "function" por
defecto de pytest-asyncio revienta esas conexiones al cerrar el loop de cada
test — no es negociable, ver el comentario en el propio `pytest.ini`. Cada
round-trip es real contra Supabase (sin mocks), así que la suite tarda más
que un test unitario típico — es el costo de que atrape bugs reales de RLS,
no una aproximación en memoria.

**Personas de prueba** (`backend/seed.py`, contraseña `Directorio2026!` para todas):
5 usuarios repartidos en 4 organizaciones (Transportes Alfa — proveedor+comprador,
publicada; Minera Beta — comprador; Ingeniería del Sur — proveedor en borrador;
Australis — proveedor, publicada, agregada en fase 7 porque el punto de control
del modo sellado necesita DOS proveedoras publicadas compitiendo por el mismo
evento, y hasta entonces solo Alfa lo estaba), más dos cuentas de backoffice sin
organización: `admin@directorioempresas.cl`
(`PLATFORM_ADMIN`, para `/admin/taxonomia`) y
`revisor.acreditacion@directorioempresas.cl` (`ACCREDITATION_REVIEWER`, para
`/admin/acreditacion`). El script es idempotente — lo vuelve a correr y
reemplaza la corrida anterior. Usar estas cuentas en vez de registrar y
otorgar roles a mano contra la base real en cada verificación.

**Storage (fase 3):** dos buckets — `org-media` (público, 8 MB, imágenes) para
logos/fotos, `org-documents` (privado, 20 MB, PDF) para fichas técnicas,
servido vía URL firmada de 1 hora. El backend habla directo con la Storage
REST API vía `httpx` (`backend/app/core/storage.py`), sin el SDK
`supabase-py` — mismo criterio que el resto del proyecto: el backend es el
único intermediario de confianza, el `service_role` nunca se expone al
cliente. Gotcha real encontrado durante la implementación: la clave de este
proyecto usa el formato nuevo `sb_secret_...` (token opaco, no JWT) — la
Storage API exige **ambos** headers `Authorization: Bearer` y `apikey` con el
mismo valor; falta uno y el error es el engañoso `"Invalid Compact JWS"`, que
no apunta a la causa real.

**Páginas públicas (fase 4):** `/discover`, `/proveedores/{slug}`,
`/sitemap.xml`, `/robots.txt` — servidas por FastAPI+Jinja2
(`backend/app/api/public.py`, `backend/app/templates/`), montadas fuera del
prefijo `/api` directamente en `app` (`backend/app/main.py`), no en la SPA de
React. HTML servido con contenido real en la respuesta inicial, sin JS
necesario para funcionar (facetas como links con querystring). CSS propio,
escrito a mano (`backend/app/static/css/public.css`) — sin un segundo build
de Tailwind, con los mismos tokens de color que `frontend/src/styles/globals.css`
copiados una vez (mantener en sync a mano si la paleta cambia). Las rutas
usan `Path(__file__).resolve()...` para ubicar `templates/`/`static/`, no
rutas relativas al CWD — el proceso puede arrancar desde la raíz del repo
(`--app-dir backend`) o desde `backend/` según el entorno.

No hay generación de tipos (`db:types`) ni suite pgTAP en este stack: los
modelos SQLAlchemy en `backend/app/models/` son el equivalente tipado, y se
mantienen a mano en sincronía con el SQL (el SQL es la fuente de verdad — los
modelos nunca corren `create_all()`).

---

## Al agregar una tabla

1. Nueva migración numerada en `backend/alembic/sql/`, con su wrapper en
   `backend/alembic/versions/` (ver `0019_taxonomy_rls_policies.py` como
   plantilla — solo hace `op.execute(SQL_FILE.read_text())`).
2. `select app.apply_table_conventions('public.tabla');` si lleva
   `updated_at`/inmutabilidad estándar.
3. `alter table … enable row level security;` **y sus policies** (sin
   `FORCE` — ver la nota extensa en `0010_hardening.sql` sobre por qué rompe
   la recursión que evitan los helpers `SECURITY DEFINER`).
4. Índice en `organization_id` (si aplica) y en toda columna que use una
   policy.
5. Fila en la matriz de [RLS.md](RLS.md).
6. Modelo SQLAlchemy en `backend/app/models/`, capa de repositorio/servicio/
   router si hace falta exponerla vía API.
7. `node scripts/db-dryrun-migrations.mjs` antes de aplicar contra la base
   real.
