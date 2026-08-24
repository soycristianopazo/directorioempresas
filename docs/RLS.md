# RLS — Referencia operativa

> Estado **implementado**. Para la estrategia completa ver [01-ARQUITECTURA.md §I](01-ARQUITECTURA.md#i-seguridad-y-estrategia-rls-en-supabase).
>
> Nota de stack: este documento asumía originalmente Supabase Auth
> (`auth.uid()`, PostgREST, pgTAP). Ese diseño se abandonó — el backend es
> FastAPI + SQLAlchemy async, con identidad propia fijada por transacción vía
> `SET LOCAL app.current_user_id` (ver `backend/app/db/rls.py`), y sin suite
> pgTAP: la verificación es manual (dry-run de migraciones + pruebas
> end-to-end contra la API real). Lo que sigue describe el estado real.

---

## Reglas del proyecto

1. **RLS activo en el 100% de las tablas.** Sin policy no se pasa. Una tabla nueva sin `enable row level security` es un bug que bloquea el merge.
2. **Toda comprobación va por un helper de `app`.** `SECURITY DEFINER` + `STABLE` + `set search_path = ''`. Sin las tres, o hay recursión, o hay lentitud, o hay escalada de privilegios.
3. **Siempre `app.current_user_id()`, nunca `current_setting(...)` suelto en una policy.** La función ya envuelve el `current_setting` con `missing_ok=true` y el cast a `uuid`; llamarla directamente se evalúa como InitPlan (una vez por sentencia, no por fila).
4. **`SET LOCAL`, nunca `SET`.** El backend conecta vía el Transaction Pooler de Supabase (Supavisor); `SET` a secas filtraría la identidad de un usuario a la siguiente petición que reutilice la misma conexión física.
5. **RLS es la defensa 1, no la única.** El servicio (`backend/app/services/*.py`) verifica el permiso relevante ANTES de mutar — no depende de que RLS bloquee un `UPDATE` y lo detecte por sus efectos.
6. **Ningún cast a un tipo de extensión (`ltree`, …) sin calificar el schema**, dentro de una función que no sea `SECURITY DEFINER`. `app_user` no tiene `extensions` en su `search_path` (a diferencia de `postgres`) — ver la nota extensa en `backend/alembic/sql/0012_admin_divisions.sql`.

---

## Helpers disponibles

| Función | Archivo | Devuelve | Uso |
|---|---|---|---|
| `app.current_user_id()` | `0002` | `uuid` | Identidad de la petición, fijada por `SET LOCAL` |
| `app.is_system_context()` | `0002` | `boolean` | ¿La transacción declaró `app.system_context = on`? (jobs, registro, invitaciones) |
| `app.is_platform_admin()` | `0007` | `boolean` | SUPER_ADMIN o PLATFORM_ADMIN |
| `app.has_platform_role(code)` | `0007` | `boolean` | Rol de plataforma concreto. SUPER_ADMIN satisface cualquiera |
| `app.has_platform_permission(perm)` | `0018` | `boolean` | Permiso de plataforma efectivo, sin organización — vía `platform_admins` + `role_permissions` |
| `app.is_member_of(org)` | `0007` | `boolean` | Membresía activa. **La condición base de casi todo** |
| `app.current_member_orgs()` | `0007` | `setof uuid` | Para `org_id in (select …)` |
| `app.has_permission(org, perm)` | `0007` | `boolean` | Permiso efectivo vía roles de organización |
| `app.effective_permissions(org)` | `0007` | `setof text` | Todos los permisos, para la UI |
| `app.org_has_capability(org, cap)` | `0007` | `boolean` | BUYER / SUPPLIER / PLATFORM_ADMIN |
| `app.viewer_has_capability(cap)` | `0007` | `boolean` | ¿Alguna org del usuario tiene esta capacidad? |
| `app.can_view_with_visibility(org, vis)` | `0007` | `boolean` | Visibilidad graduada |
| `app.maintain_hierarchy_path()` | `0012` | trigger | Calcula `level`/`path` (ltree) en `admin_divisions`/`taxonomy_nodes`/`industries` |
| `app.can_view_organization(org)` | `0028` | `boolean` | Pública si `ACTIVE`+visible, o miembro, o admin de plataforma — centraliza la lógica de visibilidad reutilizada por ~15 policies de perfil extendido |
| `app.can_view_offering(offering)` | `0028` | `boolean` | Igual que arriba pero a nivel de oferta individual, resolviendo su organización dueña |

Los helpers de arriba resuelven visibilidad para RLS. `supplier_search_index` va un paso más allá: en vez de invocar `can_view_offering()` en cada SELECT (una función `SECURITY DEFINER` con varios JOINs, cara de correr por cada fila de una búsqueda con miles de resultados), precalcula el resultado equivalente para un visitante SIN sesión en la propia columna `is_public` al reindexar — la policy de SELECT queda `using (is_public)`, una comparación de booleano plano. Es la única tabla del proyecto que cambia "función en la policy" por "columna precalculada" — deliberado, por volumen (una búsqueda facetada es exactamente el caso que no debe pagar el costo de una función por fila).

El schema `app` no se expone directamente a ningún cliente: el backend conecta como `app_user`, que tiene `USAGE` sobre `app` pero el frontend nunca ve SQL — todo pasa por las rutas de FastAPI.

---

## Matriz de acceso implementada

| Tabla | anon | Miembro/usuario | Con permiso | Plataforma |
|---|---|---|---|---|
| `users` | ✗ | Propia fila | — | Contexto de sistema (registro) |
| `profiles` | — | Propia + colegas de org | — | Lectura total (implícito vía `is_platform_admin()` en `has_permission`) |
| `organizations` | Según `visibility` (`can_view_with_visibility`) | Lectura si es miembro | `organization.update` → escritura | Total |
| `organization_capabilities` | Si la org es visible | Lectura | `organization.update` | Total |
| `organization_legal_identifiers` | ✗ | Lectura si es miembro | `organization.update` | Total |
| `permissions` | ✗ | Lectura | — | Solo lectura para `app_user` (0010 revoca escritura) |
| `roles` | ✗ | Sistema + los de su org | `role.manage` → roles custom | — |
| `organization_members` | ✗ | Propias + equipo | `member.manage` → gestión | Lectura total |
| `platform_admins` | ✗ | ✗ | — | Gestión por SUPER_ADMIN |
| `organization_invitations` | ✗ | ✗ | `member.manage` | — |
| `audit_logs` | ✗ | ✗ | `audit.read` | Lectura total |
| `domain_events` | ✗ | ✗ | ✗ | Solo contexto de sistema |
| `countries` / `currencies` / `fx_rates` / `units_of_measure` / `languages` | **Lectura total** | Lectura total | — | `platform.manage_taxonomy` → escritura |
| `admin_divisions` | **Lectura total** | Lectura total | — | `platform.manage_taxonomy` → escritura |
| `taxonomy_nodes` y relacionadas (`translations`, `synonyms`, `external_mappings`) | **Lectura total** | Lectura total | — | `platform.manage_taxonomy` → escritura |
| `industries` y `industry_translations` | **Lectura total** | Lectura total | — | `platform.manage_taxonomy` → escritura |
| `attribute_definitions` / `attribute_options` / `taxonomy_node_attributes` | **Lectura total** | Lectura total | — | `platform.manage_taxonomy` → escritura |
| `organization_locations` / `organization_contacts` / `organization_media` / `organization_settings` | Según `can_view_organization` | Lectura si es miembro | `organization.update` → escritura | Total |
| `organization_industries` / `organization_territories` | Según `can_view_organization` | Lectura si es miembro | `organization.update` → escritura | Total |
| `supplier_offerings` y relacionadas (`taxonomy_nodes`, `industries`, `territories`, `pricing`, `media`, `documents`, `attribute_values`) | Según `can_view_offering` (solo ofertas `ACTIVE` de orgs visibles) | Lectura si es miembro de la org dueña | `offering.read`/`write`/`publish`/`delete` según la acción — ver nota abajo | Total |
| `certification_types` | **Lectura total** | Lectura total | — | `platform.manage_taxonomy` → escritura (catálogo cerrado, mismo criterio que taxonomía) |
| `organization_certifications` / `client_references` / `case_studies` y relacionadas | Según `can_view_organization` (y `is_public` en la fila) | Lectura si es miembro | `organization.update` → escritura | Total |
| `supplier_search_index` | Según `is_public` (precalculado en la propia fila) | Igual que anon — el read model no distingue miembro, esa vista ya la da `/api/organizations/{id}/offerings` | `offering.write`/`publish`/`delete`/`organization.update` → escritura (reindexado, misma transacción que la mutación que lo dispara) | Total |
| `supplier_lists` / `supplier_list_items` | ✗ (nunca público, ni siquiera vía `can_view_organization`) | `vendor_list.read` (equipo comprador) | `vendor_list.manage` → escritura | Total |
| `search_logs` / `search_impressions` / `profile_views` / `offering_views` | ✗ | ✗ | ✗ | Solo contexto de sistema — sin policy de usuario, mismo criterio que `domain_events` |
| `document_types` / `accreditation_status_transitions` / `badge_definitions` | **Lectura total** | Lectura total | — | `platform.manage_taxonomy` → escritura (catálogo cerrado, mismo criterio que taxonomía) |
| `organization_documents` / `organization_document_versions` | ✗ (nunca público, ni siquiera vía `can_view_organization` — es evidencia privada) | `document.read` | `document.write`/`delete` → escritura, o `platform.review_accreditation` → solo lectura (el revisor necesita ver la evidencia, nunca alterarla) | Total |
| `accreditation_programs` / `requirement_groups` / `accreditation_requirements` | **Lectura total** (`is_active`) | Lectura total | `platform.manage_taxonomy` si `owner_scope=PLATFORM`, `organization.update` de la org dueña si `owner_scope=ORGANIZATION` | Total |
| `accreditation_enrollments` y lo que cuelga de un enrollment (`fulfillments`, `section_progress`, `status_history`) | ✗ | — | `accreditation.submit`/`manage` (la organización postulante) **o** `platform.review_accreditation` (el revisor) — backstop grueso, mismo patrón que `supplier_offerings` | Total |
| `accreditation_review_events` | ✗ | — | Igual que arriba, vía un JOIN adicional (`fulfillment → enrollment`) | Total |
| `organization_badges` | Según `can_view_organization`, solo si `revoked_at is null` | Miembro ve también sus propios badges revocados | `platform.review_accreditation` → escritura (otorgar/revocar). La organización misma **nunca** puede escribir su propio badge | Total |

**Nota sobre `supplier_offerings`:** RLS acepta cualquiera de `offering.read`/`write`/`publish`/`delete` como base para tocar la fila — es un backstop grueso. La distinción fina de CUÁL permiso hace falta para CADA mutación específica (crear/editar borrador → `write`; DRAFT→ACTIVE → `publish`, con su propia validación de completitud; borrado lógico → `delete`) vive en `services/offerings.py`, no en la policy — mismo patrón que el resto del proyecto: RLS es la defensa 1, el servicio decide el detalle.

Las tablas de referencia/taxonomía (fase 2) son deliberadamente públicas por diseño incluso para `anon`: un selector de comuna o el árbol de categorías no tiene nada que ocultar, y exponerlo permite que la landing y cualquier página pública futura lo consuman sin autenticación.

---

## Decisiones que conviene no revertir

**`organization_members` no tiene policy de INSERT directa desde el cliente.** Es deliberado. Entrar a una organización pasa exclusivamente por `services.organizations.create_organization()` o `services.team.accept_invitation()`, ambas corriendo en contexto de sistema con validación interna — nunca un `INSERT` directo del usuario.

**`organizations` tampoco tiene policy de INSERT directa.** `create_organization()` crea organización, capacidades, RUT, membresía y rol de dueño en una sola transacción de SQLAlchemy.

**`audit_logs` es inmutable de verdad.** `REVOKE UPDATE, DELETE` para `app_user`. Una auditoría que el administrador puede editar no es auditoría.

**`domain_events` tiene RLS activo y cero policies de usuario.** Es un outbox interno; solo se toca en contexto de sistema.

**Las vistas llevan `security_invoker = true`** (`v_my_organizations`, `v_effective_node_attributes`). Sin esa opción una vista corre con los privilegios de su dueño y se convierte en un agujero silencioso que rodea todas las policies de las tablas subyacentes.

**Ninguna tabla usa `FORCE ROW LEVEL SECURITY`.** `ENABLE` alcanza porque `app_user` nunca es dueño de una tabla (las crea `postgres` vía Alembic). `FORCE` rompería la vía de escape que los helpers `SECURITY DEFINER` necesitan para no recursionar contra sus propias policies — probado y reproducido una vez (`StatementTooComplexError: stack depth limit exceeded`), documentado en detalle en `0010_hardening.sql`. No reintroducir esto "por seguridad extra": es exactamente el bug ya resuelto.

**Los datos de referencia/taxonomía son de lectura pública por diseño**, con escritura acotada a `platform.manage_taxonomy`, verificado en dos capas: RLS (`app.has_platform_permission()`) y el servicio Python (mismo chequeo, antes de mutar, para evitar que RLS bloquee un `UPDATE` ya en curso).

**`supplier_search_index` se escribe con el permiso del usuario, no en contexto de sistema.** A diferencia del resto de las tablas de solo-sistema de esta fase, el reindexado (`services/search.py::reindex_offering`) corre dentro de la MISMA transacción `session_for_user()` que la mutación que lo dispara (publicar una oferta, cambiar precio, etc.) — mismo patrón que `recompute_completion_pct`. Por eso la policy de escritura acepta `offering.write`/`publish`/`delete`/`organization.update` (el mismo permiso que ya validó la mutación), no `is_system_context()`. Usar contexto de sistema aquí habría abierto una conexión NUEVA y separada, que no vería los cambios todavía sin comittear de la transacción que la disparó — el reindexado quedaría un paso atrás.

**`search_logs` / `profile_views` / `offering_views` son inmutables de verdad**, mismo criterio que `audit_logs`: `REVOKE UPDATE, DELETE` para `app_user`. `search_impressions` es la única excepción intencional — es un agregado diario incrementado por `upsert`, necesita `UPDATE`.

**Un revisor de plataforma (`ACCREDITATION_REVIEWER`) se verifica con `app.has_platform_permission()`, nunca con `app.has_permission(org, perm)`.** El revisor no es miembro de la organización postulante — `has_permission()` solo resuelve permisos vía `organization_members`/`member_roles`, así que preguntarle por el permiso de un revisor siempre da `false` sin importar qué rol de plataforma tenga. `services/accreditation.py::_require_reviewer()` y las tres policies de escritura de arriba usan `has_platform_permission('platform.review_accreditation')` — el mismo helper que ya usa `platform.manage_taxonomy` desde fase 2. Confundir estos dos helpers fue un bug real encontrado en verificación de fase 5 (`AmbiguousParameterError` en un cast de enum sin calificar en `list_review_queue`, no en el helper en sí, pero el chequeo de permiso correcto es igual de fácil de errar).

**La completitud de una acreditación (`accreditation_enrollments.completion_pct`) se recalcula en Python, no en trigger — y la vigencia se evalúa en la consulta, no se persiste.** Sin un job diario (fase 5.8, fuera de esta pasada), un `fulfillment` `APPROVED` cuyo documento venció no pasa automáticamente a `EXPIRED`. La fórmula de completitud (`repositories/accreditation.py::compute_completion`) chequea `expires_at is null or expires_at >= current_date` en la propia query — un ítem aprobado pero vencido pierde su crédito de completitud al **leer**, aunque la columna `status` guardada siga diciendo `APPROVED` hasta que algo la toque. Verificado en vivo: un ítem `APPROVED` con evidencia vencida contribuyó 0 al `completion_pct`, no 100%, exactamente como predice la fórmula.

**Supabase Storage no tiene RLS de Postgres propio en este diseño — el control de acceso vive en el backend.** El `service_role` de Storage solo lo tiene el backend (nunca el cliente); las fotos de un perfil se sirven por URL pública del bucket `org-media`, y los documentos técnicos por URL firmada de corta duración (`org-documents`, 1 hora) generada por `services/offerings.py` **después** de que el mismo chequeo de `can_view_offering()`/permiso ya pasó a nivel de API. Es el mismo principio que el resto del proyecto — RLS/permiso primero, el recurso después — aplicado a un sistema que no tiene su propio RLS.

---

## Verificación

No hay suite pgTAP en este stack. La verificación de una migración/policy nueva sigue este flujo:

1. `node scripts/db-dryrun-migrations.mjs` — aplica todo el historial de migraciones dentro de una transacción revertida, contra la base real. Detecta errores de sintaxis/orden sin arriesgar datos.
2. `alembic upgrade head` — aplicación real.
3. Verificación estructural (conteos, `select` directos) vía un script Node ad-hoc con `pg`, o `psql`.
4. Verificación de RLS end-to-end contra la API real: un usuario sin el permiso relevante debe recibir 403 (o ver un conjunto vacío en lectura filtrada); un usuario con el permiso, o el contexto de sistema, deben poder operar. Se prueba con `curl` autenticando primero vía `/api/auth/login` y usando el `access_token` devuelto.
5. Regresión: volver a correr `backend/seed.py` completo y confirmar que las fases anteriores (auth, organizaciones, equipo) siguen funcionando.

Al agregar una tabla: fila nueva en la matriz de arriba, y repetir el flujo 1-4 para esa tabla específica antes de darla por verificada.
