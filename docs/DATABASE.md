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
```

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
