# RLS — Referencia operativa

> Estado **implementado**. Para la estrategia completa ver [01-ARQUITECTURA.md §I](01-ARQUITECTURA.md#i-seguridad-y-estrategia-rls-en-supabase).

---

## Reglas del proyecto

1. **RLS activo en el 100% de las tablas.** Sin policy no se pasa. Una tabla nueva sin `enable row level security` es un bug que bloquea el merge.
2. **Toda comprobación va por un helper de `app`.** `SECURITY DEFINER` + `STABLE` + `set search_path = ''`. Sin las tres, o hay recursión, o hay lentitud, o hay escalada de privilegios.
3. **Siempre `(select auth.uid())`, nunca `auth.uid()` suelto.** El subselect se evalúa una vez por sentencia (InitPlan); la llamada directa, una vez por fila.
4. **RLS es la defensa 1, no la única.** Toda Server Action pasa además por `src/server/policies/authorize.ts`.
5. **Ninguna policy se escribe sin su prueba pgTAP.** El CI falla si el aislamiento se rompe.

---

## Helpers disponibles (`supabase/migrations/…_rls_helpers.sql`)

| Función | Devuelve | Uso |
|---|---|---|
| `app.current_user_id()` | `uuid` | `auth.uid()` cacheado |
| `app.is_platform_admin()` | `boolean` | SUPER_ADMIN o PLATFORM_ADMIN |
| `app.has_platform_role(code)` | `boolean` | Rol de plataforma concreto. SUPER_ADMIN satisface cualquiera |
| `app.is_member_of(org)` | `boolean` | Membresía activa. **La condición base de casi todo** |
| `app.current_member_orgs()` | `setof uuid` | Para `org_id in (select …)` |
| `app.has_permission(org, perm)` | `boolean` | Permiso efectivo vía roles |
| `app.effective_permissions(org)` | `setof text` | Todos los permisos, para la UI |
| `app.org_has_capability(org, cap)` | `boolean` | BUYER / SUPPLIER / PLATFORM_ADMIN |
| `app.viewer_has_capability(cap)` | `boolean` | ¿Alguna org del usuario tiene esta capacidad? |
| `app.can_view_with_visibility(org, vis)` | `boolean` | Visibilidad graduada |

El schema `app` **no está expuesto en PostgREST** (`supabase/config.toml → api.schemas`). Los dos únicos envoltorios públicos son `public.my_permissions(org)` y `public.am_i_platform_admin()`, y ambos responden solo sobre el usuario de la sesión.

---

## Matriz de acceso implementada

| Tabla | anon | Miembro | Miembro con permiso | Plataforma |
|---|---|---|---|---|
| `profiles` | ✗ | Propio + colegas (lectura) | — | Lectura total |
| `organizations` | Solo `ACTIVE` + `PUBLIC` | Lectura | `organization.update` → escritura | Total |
| `organization_capabilities` | Si la org es pública | Lectura | `organization.update` | Total |
| `organization_business_roles` | Si la org es pública | Lectura | `organization.update` | Total |
| `organization_legal_identifiers` | **✗ nunca** | Lectura | `organization.update` | Total |
| `permissions` | ✗ | Lectura | — | SUPER_ADMIN escribe |
| `roles` | ✗ | Sistema + los de su org | `role.manage` → roles custom | SUPER_ADMIN escribe |
| `role_permissions` | ✗ | Lectura de los visibles | `role.manage` | SUPER_ADMIN escribe |
| `organization_members` | ✗ | Propias + equipo | `member.manage` → UPDATE/DELETE | Lectura total |
| `member_roles` | ✗ | Lectura | `member.manage` | Total |
| `platform_admins` | ✗ | Solo la propia fila | — | SUPER_ADMIN total |
| `organization_invitations` | ✗ | ✗ | `member.manage` | — |
| `audit_logs` | ✗ | ✗ | `audit.read` | Lectura total |
| `domain_events` | ✗ | ✗ | ✗ | Solo `service_role` |

---

## Decisiones que conviene no revertir

**`organization_members` no tiene policy de INSERT.** Es deliberado. Si un usuario pudiera insertarse a sí mismo en `organization_members`, el aislamiento multiempresa completo se cae: bastaría un `INSERT` con el `organization_id` de cualquier empresa para ver todos sus datos. Entrar a una organización pasa exclusivamente por `create_organization()` o `accept_invitation()`, ambas `SECURITY DEFINER` con validación interna.

**`organizations` tampoco tiene policy de INSERT.** Un `INSERT` directo dejaría una organización sin miembros: invisible para todos, imposible de recuperar y ocupando un slug. `create_organization()` crea organización, capacidades, RUT, membresía y rol de dueño en una sola transacción.

**El RUT nunca es visible para `anon`.** Aunque el perfil sea público. Publicarlo abierto convierte el directorio en un dataset de scraping. Se expone a miembros y a compradores autenticados.

**`audit_logs` es inmutable de verdad.** `REVOKE UPDATE, DELETE, TRUNCATE` incluido para `service_role`, más un trigger `BEFORE UPDATE OR DELETE` que lanza excepción. Una auditoría que el administrador puede editar no es auditoría.

**`domain_events` tiene RLS activo y cero policies.** No es un descuido: es un outbox interno cuyo payload puede cruzar organizaciones. Solo lo consumen los workers con `service_role`.

**Las vistas llevan `security_invoker = true`.** Sin esa opción una vista corre con los privilegios de su dueño y se convierte en un agujero silencioso que rodea todas las policies de las tablas subyacentes.

---

## Pruebas

`supabase/tests/001_identity_rls.test.sql` — 34 aserciones sobre seis identidades:

| Identidad | Qué demuestra |
|---|---|
| ana (ORG_OWNER de Alfa) | Ve y administra lo suyo |
| bruno (VIEWER de Alfa) | Lee pero **no** puede editar ni administrar miembros |
| carla (dueña de Beta) | **No ve absolutamente nada** de Alfa |
| diego (miembro de Alfa y Beta) | Pertenencia múltiple real (§48) y cambio de organización |
| elena (sin organización) | No ve ninguna organización |
| anónimo | Solo perfiles `ACTIVE` + `PUBLIC`, jamás un RUT |
| admin de plataforma | Acceso transversal |

```bash
npm run db:test
```

Al agregar una tabla, agregar su fila a la matriz de arriba y sus aserciones al test. **Un test que confirma que el competidor NO ve la oferta ajena vale más que cualquier feature.**
