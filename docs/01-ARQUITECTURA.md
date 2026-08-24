# 01 · Arquitectura General

> Documento A + E + F + G + I + J del diseño técnico.
> Estado: **propuesta para validación**. No hay código escrito aún.

---

## A. Arquitectura general

### A.1 Tesis del producto

La plataforma no es un directorio ni un ERP de compras. Es una **capa de intermediación de confianza** entre demanda (compradores) y oferta (proveedores), cuyo activo defendible es un **grafo de conocimiento de proveedores** que se enriquece con cada interacción real: cada RFQ respondida, cada documento validado, cada contrato evaluado.

Esto tiene una consecuencia arquitectónica dura y no negociable:

> **La unidad atómica del sistema NO es la empresa. Es la _oferta_ (offering): un servicio o producto específico, clasificado, territorializado, con atributos técnicos, capacidad y credenciales propias.**

Una empresa de transporte no "es" transporte. *Vende* transporte de trabajadores a faena (con buses, en Antofagasta, para minería), *y también* arriendo de camionetas 4x4, *y también* escolta. Cada una tiene categoría, cobertura, atributos y acreditaciones distintas. Modelar `organización → categoría` destruye el 80% del valor del matching. Todo el diseño gira en torno a esto.

### A.2 Mapa de dominios (bounded contexts)

Doce dominios. Cada uno tiene esquema lógico propio, servicios propios y reglas RLS propias. Se comunican por FK explícitas y por un **outbox de eventos de dominio** (`domain_events`), no por triggers cruzados dispersos.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  D0 · IDENTITY & TENANCY                                                 │
│  profiles · organizations · organization_members · roles · permissions   │
│  Responde: ¿quién eres, en nombre de qué empresa actúas, qué puedes hacer│
└──────────────────────────────────────────────────────────────────────────┘
            │ todo el resto del sistema cuelga de organization_id
            ▼
┌───────────────────────────┐  ┌───────────────────────────────────────────┐
│ D1 · REFERENCE DATA       │  │ D2 · TAXONOMY & ATTRIBUTES                │
│ países · divisiones admin │  │ taxonomy_nodes (ltree) · industries       │
│ monedas · FX · UF/UTM     │  │ attribute_definitions · options · scopes  │
│ unidades de medida        │  │ Responde: ¿cómo se nombra y se filtra el  │
│ idiomas                   │  │ mundo de la oferta?                       │
└───────────────────────────┘  └───────────────────────────────────────────┘
            │                              │
            ▼                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  D3 · SUPPLY (Supplier Profile & Offerings)                              │
│  supplier_offerings · offering_taxonomy · offering_territories           │
│  offering_attribute_values · offering_pricing · media · case_studies     │
│  Responde: ¿qué vende cada empresa, dónde, con qué características?      │
└──────────────────────────────────────────────────────────────────────────┘
            │                              │
            ▼                              ▼
┌───────────────────────────┐  ┌───────────────────────────────────────────┐
│ D4 · TRUST & CREDENTIALS  │  │ D5 · DISCOVERY & SEARCH                   │
│ documentos · certificados │  │ supplier_search_index (read model)        │
│ programas de acreditación │  │ FTS (tsvector) → pgvector (V2)            │
│ badges · verificaciones   │  │ saved_searches · alerts · impressions     │
│ Responde: ¿es confiable?  │  │ Responde: ¿cómo lo encuentro?             │
└───────────────────────────┘  └───────────────────────────────────────────┘
            │                              │
            ▼                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  D6 · DEMAND & SOURCING                                                  │
│  requirements · sourcing_events · criteria (MUST/NICE) · invitations     │
│  Q&A · NDA · match_runs / match_results                                  │
└──────────────────────────────────────────────────────────────────────────┘
            ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  D7 · BIDDING & AWARD                                                    │
│  quotations → quotation_revisions (inmutables) → quotation_items         │
│  evaluations · negotiation_rounds · awards · award_approvals             │
└──────────────────────────────────────────────────────────────────────────┘
            ▼
┌───────────────────────────┐  ┌───────────────────────────────────────────┐
│ D8 · CONTRACTS (V2)       │  │ D9 · PERFORMANCE & INTELLIGENCE           │
│ contracts · milestones    │  │ performance_reviews · supplier_scores     │
│ SLA · amendments          │  │ score_components · incidents · Supplier360│
└───────────────────────────┘  └───────────────────────────────────────────┘

┌───────────────────────────┐  ┌───────────────────────────────────────────┐
│ D10 · COLLABORATION       │  │ D11 · PLATFORM OPS                        │
│ conversations · messages  │  │ audit_logs · domain_events · plans        │
│ notifications · deliveries│  │ subscriptions · entitlements · moderación │
└───────────────────────────┘  └───────────────────────────────────────────┘
```

### A.3 Arquitectura de aplicación

```
┌─────────────────────────────────────────────────────────────────┐
│  Next.js 15 (App Router) · React 19 · TypeScript strict         │
│                                                                  │
│  app/(public)      SSR/ISR · SEO · perfiles públicos            │
│  app/(auth)        login · register · onboarding                │
│  app/(app)         dashboard comprador / proveedor (RSC)        │
│  app/(admin)       backoffice plataforma                        │
│  app/api/*         solo webhooks e integraciones externas       │
└─────────────────────────────────────────────────────────────────┘
                 │                              │
   Server Actions │                              │ supabase-js (browser)
   + Route Handlers│                             │ (solo lecturas públicas
                 ▼                              ▼  y realtime)
┌─────────────────────────────────────────────────────────────────┐
│  CAPA DE ACCESO A DATOS (src/server/)                           │
│                                                                  │
│  repositories/   1 archivo por agregado. Únicos que hablan SQL. │
│  services/       reglas de negocio. Orquestan repos + eventos.  │
│  policies/       autorización a nivel aplicación (defensa 2)    │
│  schemas/        Zod: 1 esquema por comando, reusado en form    │
│  mappers/        row → dominio (nunca exponer row crudo a UI)   │
└─────────────────────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  SUPABASE                                                        │
│  PostgreSQL 15+ · ltree · pg_trgm · unaccent · pgcrypto         │
│                    (pgvector y postgis: V2)                     │
│  Auth (GoTrue) · Storage · Realtime · Edge Functions            │
│  RLS activo en el 100% de las tablas (defensa 1)                │
└─────────────────────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  TRABAJOS ASÍNCRONOS (pg_cron + Edge Functions)                 │
│  · recálculo de supplier_score (nocturno)                       │
│  · detección de documentos por vencer (diario)                  │
│  · refresh de supplier_search_index (por trigger + full nocturno)│
│  · despacho de notificaciones desde domain_events               │
│  · alertas de búsquedas guardadas y oportunidades               │
│  · agregación de marketplace_metrics_daily                      │
└─────────────────────────────────────────────────────────────────┘
```

### A.4 Cinco decisiones arquitectónicas de fondo

| # | Decisión | Alternativa descartada | Por qué |
|---|---|---|---|
| 1 | **Offering como unidad atómica** de clasificación, cobertura, atributos y matching | `organization.category_id` | Sin esto el matching es ruido. Es el habilitador del Knowledge Graph. |
| 2 | **Dos taxonomías independientes**: *qué vendes* (taxonomy_nodes) y *a qué industria sirves* (industries) | Un solo árbol `Industria → Categoría → …` como venía en el brief §7 | Son ejes ortogonales. "Transporte de personas" se vende a minería, construcción y retail. Mezclarlos obliga a duplicar toda la rama de transporte bajo cada industria. **Corrección explícita al brief.** |
| 3 | **Cotizaciones inmutables por revisión**: `quotation_revisions` append-only, `quotation_items` cuelga de la revisión | Actualizar `quotations` in-place con historial en tabla espejo | La inmutabilidad estructural hace imposible perder trazabilidad por un `UPDATE` mal escrito. Requisito §27 y §77. |
| 4 | **EAV tipado con columnas por tipo + proyección JSONB derivada** | (a) JSONB puro, (b) EAV con `value text` | (a) mata integridad y matching; (b) mata tipos y comparaciones numéricas. La proyección JSONB es **derivada, nunca fuente de verdad**. |
| 5 | **Read model desnormalizado para búsqueda** (`supplier_search_index`) | Consultar en vivo el modelo normalizado con 8 JOINs | Búsqueda facetada sobre EAV + jerarquías + geografía no escala en OLTP. Read model refrescado por trigger. |

### A.5 Convenciones transversales

- **PK**: `uuid` (`gen_random_uuid()`) en toda tabla de dominio. `smallint`/`text` en catálogos estables (`countries.code = 'CL'`, `currencies.code = 'CLP'`).
- **Timestamps**: `created_at timestamptz not null default now()`, `updated_at` mantenido por trigger `set_updated_at()`.
- **Autoría**: `created_by uuid references profiles(id)`, `updated_by` en toda tabla con escritura de usuario.
- **Soft delete**: `deleted_at timestamptz` **solo** donde el borrado es reversible y el objeto es referenciable (organizaciones, offerings, documentos, listas). Nunca en tablas transaccionales de proceso (cotizaciones, adjudicaciones): ahí el estado es `status`, no borrado.
  - Todo índice único convive con soft delete vía índice parcial: `unique (org_id, slug) where deleted_at is null`.
- **Estados**: ENUM nativo de Postgres cuando el conjunto es cerrado y del núcleo (`quotation_status`); tabla catálogo cuando el negocio puede agregar valores sin deploy (`document_types`, `badge_definitions`).
- **Dinero**: nunca un `numeric` suelto. Siempre la tripleta `amount numeric(18,4)` + `currency_code` + `amount_base numeric(18,4)` (snapshot convertido con `fx_rate_snapshot` y `fx_rate_date`). Ver §I del riesgo multi-moneda en `04-ROADMAP.md`.
- **Nombres**: tablas en plural, snake_case, inglés. Datos de negocio y UI en español (es-CL). Catálogos con tabla de traducciones.
- **Migraciones**: `supabase/migrations/NNNN_descripcion.sql`, forward-only, idempotentes donde sea posible, nunca cambios manuales en el dashboard.

---

## E. Arquitectura multiempresa (multitenancy)

### E.1 El modelo

```
auth.users (Supabase)
     │ 1:1
     ▼
profiles ─────┐
              │ N
              ▼
       organization_members ◄──── N ──── organizations
              │ N                              │ N
              ▼                                ▼
        member_roles ──► roles         organization_capabilities
                          │ N            (BUYER, SUPPLIER, ...)
                          ▼
                    role_permissions ──► permissions
```

**Reglas duras:**

1. **Nunca `profiles.organization_id`.** Una persona pertenece a N organizaciones (consultor que asesora a tres mineras, holding con varias razones sociales). La pertenencia vive en `organization_members(user_id, organization_id)` con `unique(user_id, organization_id)`.

2. **Una organización no tiene "tipo", tiene capacidades.** `organization_capabilities(organization_id, capability)` con `capability ∈ {BUYER, SUPPLIER, PLATFORM_ADMIN}`. Una empresa contratista es comprador *y* proveedor simultáneamente y eso es lo normal, no la excepción (§4). Los roles de negocio adicionales (mandante, contratista, OTEC, fabricante, distribuidor) son **atributos declarativos** (`organization_business_roles`), no capacidades de sistema: no cambian permisos, cambian filtros y presentación.

3. **Un miembro tiene N roles.** `member_roles(member_id, role_id)`. Un jefe de abastecimiento puede ser `BUYER_MANAGER` + `CONTRACT_MANAGER`. Modelarlo como un solo `role` enum en `organization_members` obliga a inventar roles combinados.

4. **Organización activa = decisión de UI, verificada en el servidor.** El `active_org_id` se guarda en cookie y se valida en cada Server Action contra `organization_members`. **No se inyecta en el JWT.**
   - *Por qué:* un claim en `app_metadata` exige refrescar el token en cada cambio de organización, se desincroniza si revocas la membresía y complica la revocación inmediata. RLS valida **membresía**, no "org activa"; el scoping por org activa lo hace la capa de aplicación. Coste: cada consulta debe filtrar explícitamente por `organization_id`. Beneficio: revocación instantánea y cero superficie de token obsoleto.

5. **Aislamiento por defecto.** Toda tabla de dominio lleva `organization_id` (o llega a él por un único salto de FK) y tiene RLS con `deny by default`.

### E.2 Roles

| Ámbito | Rol | Alcance |
|---|---|---|
| Plataforma | `SUPER_ADMIN` | Todo, incluido impersonación auditada |
| Plataforma | `PLATFORM_ADMIN` | Backoffice, taxonomía, moderación, planes |
| Plataforma | `ACCREDITATION_REVIEWER` | Revisar y validar documentación de acreditación |
| Plataforma | `SUPPORT_AGENT` | Lectura de soporte, sin datos comerciales sensibles |
| Empresa | `ORG_OWNER` | Todo dentro de la organización, incluido facturación y borrado |
| Empresa | `ORG_ADMIN` | Equipo, perfil, configuración |
| Empresa | `BUYER_MANAGER` | Crear/gestionar eventos, adjudicar, aprobar dentro de su DoA |
| Empresa | `BUYER` | Crear requerimientos y eventos, sin adjudicar |
| Empresa | `PROCUREMENT_ANALYST` | Analítica, vendor list, comparador, sin adjudicar |
| Empresa | `CONTRACT_MANAGER` | Contratos, SLA, evaluaciones de desempeño |
| Empresa | `SUPPLIER_ADMIN` | Perfil de proveedor, catálogo, acreditación |
| Empresa | `SALES` | Oportunidades, cotizaciones, mensajería |
| Empresa | `EVALUATOR` | Solo evaluar en eventos donde fue asignado |
| Empresa | `VIEWER` | Solo lectura |

**Evolución a permisos granulares sin refactor:** los roles no se chequean por nombre. Se chequea `has_permission(org_id, 'sourcing_event.award')`. La tabla `permissions` arranca con ~60 permisos atómicos y `role_permissions` los agrupa. Cuando un cliente enterprise pida roles a medida, se crea una fila en `roles` con `organization_id` no nulo (rol custom de esa empresa) y se le asignan permisos. Cero cambio de código.

**Separación de deberes (SoD):** `EVALUATOR` no puede ver la oferta económica hasta que la evaluación técnica esté cerrada; quien crea el evento no puede aprobar la adjudicación si el monto excede su `approval_limit`. Esto se modela en `award_approvals` + `organization_approval_policies` (ver mejora N.12).

---

## F. Arquitectura del módulo de acreditación

### F.1 El problema real

El error clásico es modelar "la acreditación" como un campo `organizations.accreditation_status`. Eso rompe el requisito §13: un proveedor puede estar acreditado para servicios TI y **no** para trabajos eléctricos de alto riesgo; acreditado ante Codelco pero no ante BHP.

**La acreditación es una relación `(organización, programa)`, no un atributo de la organización.**

### F.2 Las cinco piezas

```
① REPOSITORIO ÚNICO DE EVIDENCIA (nivel organización, se sube UNA vez)
   organization_documents ──► organization_document_versions
   organization_certifications
   El F30 se sube una vez y sirve para los 14 programas. Este es el
   principal argumento de venta hacia el proveedor: fin del re-tipeo.

② DEFINICIÓN DE EXIGENCIAS
   accreditation_programs
     owner_scope: PLATFORM | ORGANIZATION
     owner_organization_id (null si PLATFORM)
     applies_to: taxonomy_node_id? · industry_id? · risk_level? · country?
   accreditation_requirements  (ítems del programa)
     requirement_kind: DOCUMENT | CERTIFICATION | ATTRIBUTE | DECLARATION | FORM
     is_mandatory · weight · min_validity_days · reviewer_role

③ ESTADO POR PROGRAMA
   accreditation_enrollments  (organization × program)
     status · completion_pct · score · valid_from · valid_until
     Es la tabla que responde "¿está acreditada esta empresa para esto?"

④ CUMPLIMIENTO ÍTEM A ÍTEM
   accreditation_fulfillments (enrollment × requirement)
     evidence: document_version_id | certification_id | attribute_value
     status: PENDING | SUBMITTED | UNDER_REVIEW | OBSERVED | APPROVED | REJECTED | EXPIRED
     reviewer_id · reviewed_at · observation

⑤ HISTORIA (append-only, nunca UPDATE destructivo)
   accreditation_status_history
   accreditation_review_events
```

### F.3 Estados y máquina

```
INCOMPLETE ──► PENDING_DOCUMENTS ──► UNDER_REVIEW ──┬──► ACCREDITED ──► EXPIRED
                      ▲                              │        │             │
                      │                              ├──► OBSERVED ─────────┘
                      └──────────────────────────────┘        │
                                                              ├──► SUSPENDED
                                                              └──► REJECTED
```

Transiciones válidas en tabla `accreditation_status_transitions` (no en código): permite auditar y ajustar sin deploy.

### F.4 Completitud

`completion_pct` **no** es un único número. Es un vector por sección, calculado como función determinística:

```
completion_pct(enrollment) = Σ (requirement.weight × fulfillment_factor) / Σ requirement.weight

fulfillment_factor = 1.0  si APPROVED y vigente
                     0.5  si SUBMITTED o UNDER_REVIEW
                     0.0  si PENDING, REJECTED o EXPIRED
```

Se materializa en `accreditation_enrollments.completion_pct` vía trigger sobre `accreditation_fulfillments`, y se desglosa por `requirement_group` (Perfil / Tributario / Legal / SSO / Financiero / Experiencia) en `accreditation_section_progress`, que es exactamente la vista del §11 del brief.

### F.5 Vencimientos (motor de retención)

`accreditation_fulfillments.expires_at` se deriva de `organization_document_versions.valid_until`. Un job diario:
1. marca `EXPIRED` lo vencido → recalcula `completion_pct` → puede degradar el enrollment a `PENDING_DOCUMENTS`;
2. emite `domain_event` a 30/15/7/1 días → notificación al proveedor **y** al comprador que lo tiene en su AVL.

Este job es, en la práctica, la funcionalidad que hace que abastecimiento entre a la plataforma cada semana.

### F.6 Badges

`badge_definitions(code, name, rule_expression jsonb, is_automatic, validity_days)` + `organization_badges(organization_id, badge_id, granted_at, expires_at, evidence jsonb, granted_by)`.

Las reglas son **datos**, evaluados por un evaluador determinístico:
```json
{ "all": [
    { "fact": "accreditation.PLATFORM_BASE.status", "op": "=",  "value": "ACCREDITED" },
    { "fact": "documents.expired_count",            "op": "=",  "value": 0 },
    { "fact": "supplier_score.total",               "op": ">=", "value": 80 }
]}
```
Nunca badges hardcodeados en TypeScript. Nunca badges comprables con el plan (ver §58 del brief y mejora N.20).

---

## G. Arquitectura del proceso Necesidad → Adjudicación

### G.1 Flujo completo

```
┌── INTAKE ────────────────────────────────────────────────────────┐
│ requirements                                                     │
│ Origen A: formulario estructurado                                │
│ Origen B: texto libre → (V2) IA estructura → SIEMPRE confirma    │
│           un humano antes de persistir                           │
│ Origen C: selección desde Discovery ("cotizar a estos 6")        │
│ status: DRAFT → READY → CONVERTED → CANCELLED                    │
└──────────────────────────────────────────────────────────────────┘
        │  0..N eventos por requerimiento (permite dividir por lote)
        ▼
┌── SOURCING EVENT ────────────────────────────────────────────────┐
│ sourcing_events  type: RFI | RFQ | RFP | QUICK_BUY | DIRECT_AWARD│
│                  visibility: PUBLIC|NETWORK|INVITED_ONLY|PRIVATE │
│                  bid_mode: OPEN | SEALED                         │
│ ├── sourcing_event_lots / _items    (qué se cotiza, línea a línea)│
│ ├── sourcing_event_criteria         (MUST_HAVE / NICE_TO_HAVE)   │
│ ├── sourcing_event_stages           (fechas: consultas, ofertas, │
│ │                                    apertura, adjudicación)     │
│ └── sourcing_event_documents · nda_requirement                   │
└──────────────────────────────────────────────────────────────────┘
        ▼
┌── MATCHING (determinístico) ─────────────────────────────────────┐
│ match_runs (una corrida, con weights_snapshot y engine_version)  │
│ match_results (organization_id, offering_id, score,              │
│                is_eligible, blocking_reasons[], breakdown jsonb) │
│ Reproducible: misma entrada + misma versión = mismo resultado    │
└──────────────────────────────────────────────────────────────────┘
        ▼
┌── INVITACIÓN ────────────────────────────────────────────────────┐
│ sourcing_event_invitations                                       │
│ status: INVITED → VIEWED → NDA_ACCEPTED → INTERESTED →           │
│         PARTICIPATING → QUOTED → SHORTLISTED → NEGOTIATING →     │
│         AWARDED | NOT_AWARDED | DECLINED | NO_RESPONSE           │
│ invitation_status_history: cada transición con timestamp y actor │
│ decline_reason_code: permite analítica de por qué no cotizan     │
└──────────────────────────────────────────────────────────────────┘
        ▼
┌── Q&A ───────────────────────────────────────────────────────────┐
│ sourcing_questions (asked_by_organization_id)                    │
│ sourcing_answers   (visibility: PRIVATE_TO_ASKER | ALL_PARTICIPANTS)│
│ Regla: responder a todos NO revela quién preguntó                │
└──────────────────────────────────────────────────────────────────┘
        ▼
┌── COTIZACIÓN ────────────────────────────────────────────────────┐
│ quotations            (1 por proveedor por evento — contenedor)  │
│   └── quotation_revisions  APPEND-ONLY, round_number, is_current │
│         ├── quotation_items      (línea a línea, contra event_items)│
│         ├── quotation_responses  (respuesta a cada criterio)     │
│         └── quotation_documents                                  │
│ SEALED: el comprador no ve NADA económico hasta opened_at.       │
│         Se fuerza en RLS, no en la UI.                           │
└──────────────────────────────────────────────────────────────────┘
        ▼
┌── EVALUACIÓN ────────────────────────────────────────────────────┐
│ evaluation_templates → evaluation_criteria (peso por dimensión)  │
│ dimensiones: TECHNICAL · COMMERCIAL · HSE · LEGAL · FINANCIAL    │
│ evaluation_assignments (comité: quién evalúa qué dimensión)      │
│ evaluations + evaluation_scores (evaluador × cotización × criterio)│
│ Score consolidado = Σ(peso_dimensión × promedio_evaluadores)     │
│ El sistema NUNCA adjudica solo. Sugiere, ordena, explica.        │
└──────────────────────────────────────────────────────────────────┘
        ▼
┌── NEGOCIACIÓN ───────────────────────────────────────────────────┐
│ negotiation_rounds (round_type: INITIAL | COUNTER | BAFO)        │
│ Cada ronda abre una nueva quotation_revision. La anterior queda  │
│ intacta y consultable. Nunca se sobrescribe.                     │
└──────────────────────────────────────────────────────────────────┘
        ▼
┌── ADJUDICACIÓN ──────────────────────────────────────────────────┐
│ awards + award_items (permite adjudicación parcial / multi-prov.)│
│ award_approvals (cadena DoA según monto y política de la empresa)│
│ → notifica a TODOS los participantes (adjudicados y no)          │
│ → opcionalmente crea purchase_order y/o contract                 │
│ → alimenta supplier_scores y buyer_supplier_relationships        │
└──────────────────────────────────────────────────────────────────┘
        ▼
┌── DESEMPEÑO ─────────────────────────────────────────────────────┐
│ supplier_performance_reviews (post-servicio, 8 dimensiones)      │
│ Solo evaluable por quien tuvo un award o contract real → reviews │
│ verificadas, no opinables. Realimenta supplier_score y matching. │
└──────────────────────────────────────────────────────────────────┘
```

### G.2 Por qué `requirements` y `sourcing_events` son tablas distintas

Tentación razonable: fusionarlas. Se mantienen separadas porque:
- Un requerimiento puede **no** convertirse nunca en evento (intake, sondeo de mercado, RFI exploratorio) y aun así es dato valioso para *demand intelligence* y para medir liquidez por categoría.
- Un requerimiento grande se divide en **varios eventos** (por lote, por región, por especialidad).
- El requerimiento es el objeto que el comprador entiende ("necesito X"); el evento es el objeto de proceso con reglas, fechas y participantes. Ciclos de vida distintos.

Coste: un JOIN extra y disciplina para no duplicar campos. Aceptable.

### G.3 Sealed bid: la regla de confidencialidad crítica

En `bid_mode = SEALED`, ninguna fila de `quotation_revisions` / `quotation_items` de un proveedor es visible para el comprador antes de `sourcing_event_stages.bid_opening_at`. Esto se garantiza en la **policy RLS**, y la apertura queda registrada en `audit_logs` con quién abrió y cuándo (ceremonia de apertura). Si se implementa solo en la UI, es una filtración esperando ocurrir — y en licitaciones mineras es un incidente terminal para la reputación de la plataforma.

Un proveedor **jamás** ve ofertas de otro proveedor, en ningún modo, en ningún estado.

---

## I. Seguridad y estrategia RLS en Supabase

### I.1 Principios

1. **Deny by default.** `alter table X enable row level security;` sin policy = nadie accede. Se activa RLS en el 100% de las tablas, incluidas las de catálogo (con policy `select` para `authenticated`/`anon` donde corresponda).
2. **RLS es la defensa 1, no la única.** La capa `policies/` en el servidor vuelve a validar. Un bug en una policy no debe ser el único obstáculo.
3. **`service_role` solo en jobs y Edge Functions**, nunca alcanzable desde el navegador ni desde una Server Action que reciba input de usuario sin validar.
4. **Funciones helper `SECURITY DEFINER` + `STABLE`** para romper recursión de policies y permitir caching del planner.

### I.2 Funciones helper (el corazón del sistema)

```sql
-- Todas: SECURITY DEFINER, STABLE, search_path = '', REVOKE de public.
auth_uid()                                  -- (select auth.uid()) cacheado
is_platform_admin()                         -- rol de plataforma
is_member_of(org uuid)                      -- membresía activa
has_permission(org uuid, perm text)         -- permiso efectivo vía roles
current_member_orgs()                       -- setof uuid, para IN (...)
can_view_event(event uuid)                  -- dueño, invitado o público
owns_quotation(quotation uuid)              -- proveedor dueño
can_view_quotation(quotation uuid)          -- dueño OR (comprador AND sealed abierto)
```

> **Nota de rendimiento crítica:** dentro de una policy, `auth.uid()` se re-evalúa por fila. Escribir siempre `(select auth.uid())` para que Postgres lo trate como InitPlan y lo evalúe una vez. En tablas grandes la diferencia es de dos órdenes de magnitud.

### I.3 Patrones de policy

**Patrón A — Datos propios de la organización** (`organization_contacts`, `supplier_offerings`, `organization_documents`):
```
SELECT : is_member_of(organization_id)
         OR (visibility = 'PUBLIC' AND deleted_at IS NULL)
INSERT/UPDATE/DELETE : has_permission(organization_id, '<recurso>.write')
```

**Patrón B — Catálogos públicos** (`countries`, `taxonomy_nodes`, `industries`, `attribute_definitions`):
```
SELECT : true (anon + authenticated)
WRITE  : is_platform_admin()
```

**Patrón C — Perfil público con visibilidad graduada** (§57, §86):
`visibility ∈ {PUBLIC, REGISTERED, BUYERS_ONLY, INVITED_ONLY, PRIVATE}` en la propia fila.
```
SELECT : is_member_of(organization_id)
      OR visibility = 'PUBLIC'
      OR (visibility = 'REGISTERED'   AND auth_uid() IS NOT NULL)
      OR (visibility = 'BUYERS_ONLY'  AND viewer_has_capability('BUYER'))
      OR (visibility = 'INVITED_ONLY' AND has_active_invitation(organization_id))
```

**Patrón D — Proceso de sourcing** (`sourcing_events`):
```
SELECT : is_member_of(buyer_organization_id)                       -- dueño
      OR EXISTS (invitación vigente para una de mis orgs)          -- invitado
      OR (visibility='PUBLIC' AND status IN ('PUBLISHED','OPEN'))  -- abierto
```

**Patrón E — Cotizaciones (la más delicada)** (`quotations`, `quotation_revisions`, `quotation_items`):
```
SELECT :
   is_member_of(supplier_organization_id)                        -- el proveedor: siempre la suya
OR (
     is_member_of( evento.buyer_organization_id )
     AND has_permission(evento.buyer_organization_id,'quotation.read')
     AND ( evento.bid_mode = 'OPEN' OR evento.bid_opened_at IS NOT NULL )
     AND ( NOT es_evaluador_tecnico_con_bloqueo_economico )
   )
OR is_platform_admin_con_motivo_auditado()

INSERT : is_member_of(supplier_org) AND invitación en estado válido
         AND now() <= deadline_ofertas
UPDATE : PROHIBIDO sobre revisiones enviadas. Solo se inserta nueva revisión.
```

**Patrón F — Mensajería**:
```
SELECT/INSERT : EXISTS (conversation_participants donde participant_org ∈ current_member_orgs())
```

**Patrón G — Documentos privados**: nunca URL pública. `createSignedUrl` con TTL ≤ 5 min, generada en el servidor **después** de validar permiso en la capa de aplicación. Toda descarga de documento de acreditación o contractual se registra en `audit_logs`.

### I.4 Testing de RLS (no negociable)

Suite `pgTAP` que, por cada tabla sensible, prueba con al menos 6 identidades: dueño, miembro sin permiso, comprador invitado, comprador no invitado, proveedor competidor, anónimo. **Un test que confirma que el competidor NO ve la oferta ajena vale más que cualquier feature.** Corre en CI y bloquea el merge.

### I.5 Otras medidas

- Validación Zod en el borde de toda Server Action; nunca confiar en el cliente.
- Storage: whitelist MIME + límite de tamaño por bucket + verificación de *magic bytes* en Edge Function, no solo de extensión.
- Rate limiting por IP y por organización en búsqueda, mensajería, invitaciones y subida de archivos.
- Auditoría inmutable: `audit_logs` sin UPDATE ni DELETE (revocado incluso para `service_role`), particionada por mes.
- Impersonación de soporte: permitida solo a `SUPER_ADMIN`, con motivo obligatorio, ventana temporal y registro en `audit_logs`.
- Realtime: suscripciones solo a canales cuyos datos pasen RLS; **nunca** exponer `quotation_items` por Realtime en eventos sellados.

---

## J. Storage: buckets y política

| Bucket | Público | Contenido | Límite | MIME permitidos |
|---|---|---|---|---|
| `org-public-media` | ✅ | Logos, banners, fotos y video corporativo del perfil público | 10 MB | image/*, video/mp4 |
| `offering-media` | ✅ | Fotos y videos de productos/servicios | 10 MB | image/*, video/mp4 |
| `case-study-media` | ✅ | Evidencias de casos de éxito publicables | 10 MB | image/*, application/pdf |
| `public-datasheets` | ✅ | Fichas técnicas que el proveedor decide publicar | 20 MB | application/pdf |
| `org-private-docs` | ❌ | Repositorio legal/tributario/financiero (F30, carpeta tributaria, EEFF) | 25 MB | pdf, jpg, png |
| `certifications` | ❌ | ISO, mutualidad, pólizas | 25 MB | pdf, jpg, png |
| `accreditation-evidence` | ❌ | Evidencia adjunta a fulfillments | 25 MB | pdf, xlsx, jpg |
| `sourcing-docs` | ❌ | Bases, planos, especificaciones de RFQ (bajo NDA si aplica) | 100 MB | pdf, dwg, xlsx, zip |
| `quotation-docs` | ❌ | Anexos de oferta | 100 MB | pdf, xlsx, zip |
| `contract-docs` | ❌ | Contratos, anexos, boletas de garantía, estados de pago | 50 MB | pdf |
| `message-attachments` | ❌ | Adjuntos de mensajería | 25 MB | pdf, image/*, xlsx |
| `platform-assets` | ✅ | Assets del sistema (íconos de categoría, plantillas descargables) | 5 MB | image/*, pdf |

**Convención de path (habilita RLS por prefijo):**
```
{bucket}/{organization_id}/{entity_type}/{entity_id}/{uuid}_{slug}.{ext}
```
La policy de `storage.objects` extrae el `organization_id` con `(storage.foldername(name))[1]::uuid` y lo valida contra la membresía. Para `sourcing-docs` la regla es la del evento (dueño o invitado con NDA aceptado si el evento lo exige).

**Reglas fijas:**
- Ningún bucket privado se vuelve público "temporalmente". Se usan signed URLs, siempre.
- Todo archivo tiene fila espejo en la base (`*_documents` / `*_media`) con `storage_path`, `mime_type`, `size_bytes`, `checksum_sha256`, `uploaded_by`. La base es el índice; Storage es solo el blob.
- Antivirus (Edge Function → servicio externo) en buckets privados antes de marcar el documento como `AVAILABLE`. En MVP: cuarentena + validación de magic bytes; escaneo real en V1.
- Retención: los documentos de procesos cerrados no se borran (requisito legal y de auditoría); se mueven a clase de almacenamiento fría en V2.

---

## Continúa en

- **[02-MODELO-DATOS.md](02-MODELO-DATOS.md)** — B (tablas), C (diagramas ER), D (taxonomía y atributos)
- **[03-MATCHING-ENGINE.md](03-MATCHING-ENGINE.md)** — H (fórmula, variables, explicabilidad)
- **[04-ROADMAP.md](04-ROADMAP.md)** — K (MVP/V1/V2), L (orden de desarrollo), M (riesgos)
- **[05-MEJORAS-PROPUESTAS.md](05-MEJORAS-PROPUESTAS.md)** — N (20 mejoras al diseño)
