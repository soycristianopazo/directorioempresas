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
4 usuarios repartidos en 3 organizaciones (Transportes Alfa — proveedor+comprador,
publicada; Minera Beta — comprador; Ingeniería del Sur — proveedor en borrador),
más dos cuentas de backoffice sin organización: `admin@directorioempresas.cl`
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
