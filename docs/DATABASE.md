# Base de datos — Estado implementado

> Diseño completo (~112 tablas) en [02-MODELO-DATOS.md](02-MODELO-DATOS.md).
> Este documento cubre **lo que existe hoy en `supabase/migrations/`**.

---

## Migraciones

| Archivo | Contenido |
|---|---|
| `…0001_extensions_and_conventions.sql` | Extensiones, schema `app`, ENUMs raíz, triggers estándar, `slugify`, validación de RUT |
| `…0002_profiles.sql` | `profiles` + trigger de alta desde `auth.users` |
| `…0003_organizations.sql` | `organizations`, capacidades, roles de negocio, identificadores tributarios |
| `…0004_rbac.sql` | `permissions`, `roles`, `role_permissions`, `organization_members`, `member_roles`, `platform_admins`, invitaciones |
| `…0005_audit_and_events.sql` | `audit_logs` particionada e inmutable, `domain_events` (outbox) |
| `…0006_rls_helpers.sql` | Funciones helper de RLS |
| `…0007_rls_policies_identity.sql` | Policies del dominio D0 |
| `…0008_seed_roles_permissions.sql` | Catálogo de 46 permisos y 14 roles de sistema |
| `…0009_organization_rpcs.sql` | `create_organization`, `accept_invitation`, `switch_organization`, `remove_member`, vista `v_my_organizations`, envoltorios públicos |

Forward-only. **Nunca editar una migración ya aplicada**: se agrega una nueva.

---

## Convenciones

- **PK** `uuid` con `gen_random_uuid()`. Catálogos estables usan su código natural (`permissions.code`).
- **Timestamps** `created_at` / `updated_at` con trigger `app.set_updated_at()`. `created_at` es inmutable por trigger.
- **Autoría** `created_by` / `updated_by` → `profiles(id)` con `on delete set null`.
- **Soft delete** solo donde el objeto es referenciable y el borrado reversible. Hoy: `organizations`. Todo índice único convive con él vía índice parcial `where deleted_at is null`.
- **ENUM** para conjuntos cerrados del núcleo; tabla catálogo para lo que el negocio pueda ampliar sin deploy.
- **Dinero** siempre `(amount, currency_code, amount_base)` + `fx_rate_snapshot`. Aún no hay tablas de dinero; la convención rige desde la fase 7.
- Aplicar convenciones a una tabla nueva: `select app.apply_table_conventions('public.mi_tabla');`

---

## Tablas implementadas

### Identidad

**`profiles`** — 1:1 con `auth.users`, creada por el trigger `on_auth_user_created`.
`full_name` es columna generada. `last_org_id` es una **sugerencia de UI**, nunca fuente de autorización.
**No tiene `organization_id`**: la pertenencia vive en `organization_members` (§48 del brief).

**`organizations`** — La empresa. Sin campo `type`: ver `organization_capabilities`.
`slug` único entre organizaciones vivas. `is_claimed = false` marca perfiles pre-cargados aún no reclamados (mejora N.6); un perfil no reclamado no puede salir de `DRAFT`.

**`organization_capabilities`** — `BUYER` / `SUPPLIER` / `PLATFORM_ADMIN`. Afectan permisos y navegación.

**`organization_business_roles`** — `MANDANTE`, `CONTRATISTA`, `OTEC`, … Declarativos: **no** afectan permisos.

**`organization_legal_identifiers`** — Multi-país. El RUT chileno se valida por módulo 11 con un `CHECK` que llama a `app.is_valid_rut()`, y se normaliza a `76086428-5` por trigger antes de insertar, de modo que el índice único funcione con independencia del formato que escriba el usuario.

### RBAC

**`permissions`** — 46 permisos atómicos con formato `recurso.acción`.
**Regla:** el código nunca compara nombres de rol. Chequea `has_permission(org, 'sourcing_event.award')`. Eso permite roles a medida por empresa sin tocar TypeScript.

**`roles`** — 14 roles de sistema (4 de plataforma, 10 de organización).
`organization_id is null` → rol de sistema. `organization_id` no nulo → rol custom de esa empresa.

**`organization_members`** — `unique(user_id, organization_id)`. Incluye `approval_limit_amount` para la cadena DoA de la fase 8 (mejora N.9).

**`member_roles`** — Un miembro, N roles. Un trigger impide asignar un rol de otra organización o un rol de plataforma.

**`platform_admins`** — Roles de plataforma, separados de la membresía de empresa.

**`organization_invitations`** — Se almacena **solo el hash SHA-256** del token. Si la tabla se filtra, las invitaciones pendientes siguen sin ser canjeables. Índice parcial: una sola invitación pendiente por email y organización.

### Observabilidad

**`audit_logs`** — Particionada por mes (`app.ensure_audit_partitions()` crea 24 meses por adelantado; se agenda con `pg_cron` en la fase 2). Sin FK a propósito: el registro debe sobrevivir al borrado de lo auditado. Inmutable: `REVOKE` + trigger.

**`domain_events`** — Outbox transaccional. Los triggers escriben aquí con `app.emit_event()`; los workers consumen. **Nunca enviar un correo desde un trigger.**

---

## Funciones invocables

| Función | Quién | Qué hace |
|---|---|---|
| `create_organization(nombre, comercial, rut, capacidades, país)` | `authenticated` | Organización + capacidades + RUT + membresía + rol de dueño, **en una transacción** |
| `accept_invitation(token)` | `authenticated` | Valida hash, vigencia y coincidencia de correo; crea la membresía |
| `switch_organization(org_id)` | `authenticated` | Persiste la preferencia tras validar la membresía |
| `remove_member(member_id)` | `authenticated` | Remueve validando que no quede la organización sin dueño |
| `my_permissions(org_id)` | `authenticated` | Permisos efectivos del usuario de la sesión |
| `am_i_platform_admin()` | `authenticated` | Rol de plataforma del usuario de la sesión |

---

## Entorno local

Requiere **Docker** (Supabase local levanta Postgres, GoTrue, Storage y Studio en contenedores).

```bash
npx supabase start
npx supabase db reset
npm run db:types
```

`db reset` aplica las 9 migraciones y ejecuta `supabase/seed.sql` (4 usuarios y 2 organizaciones de prueba; contraseña `Password123`).

Sin Docker, las migraciones se aplican a un proyecto Supabase hospedado:

```bash
npx supabase link --project-ref <ref>
npx supabase db push
npm run db:types:remote
```

---

## Al agregar una tabla

1. Nueva migración numerada; nunca editar una existente.
2. `select app.apply_table_conventions('public.tabla');`
3. `alter table … enable row level security;` **y sus policies**.
4. Índice en `organization_id` y en toda columna que use una policy.
5. Fila en la matriz de [RLS.md](RLS.md) y aserciones en `supabase/tests/`.
6. `npm run db:types` para regenerar los tipos.
