# Plataforma B2B de Proveedores, Abastecimiento y Cotizaciones

> Supplier Discovery + Supplier Network + Procurement Marketplace + RFQ Management + Supplier Qualification
> Diseñada para Chile. Arquitectura multi-país, multi-moneda y multiempresa desde el día 1.

**Estado: Fase 0 y Fase 1 implementadas** (fundaciones + identidad y multitenancy). Fases 2 a 8 en [04-ROADMAP.md](docs/04-ROADMAP.md).

### Decisiones cerradas

| Fecha | Decisión | Consecuencia |
|---|---|---|
| 2026-08-23 | **Dos taxonomías ortogonales**: `taxonomy_nodes` (qué vendes) × `industries` (a qué industria sirves). Se descarta el árbol único `Industria → Categoría → …` del brief §7. | La rama de cada categoría existe una sola vez. Un offering se clasifica en 1..N nodos × 1..N industrias × 1..N territorios. La UI sigue presentándose como árbol navegable de dos ejes. |
| 2026-08-23 | **MVP = supply-side + discovery** (10 semanas). RFQ, matching y cotizaciones entran en V1. | El MVP cierra al completar la Fase 5 (acreditación). Métricas de salida en [04-ROADMAP.md](docs/04-ROADMAP.md#-mvp--encuéntrame-semanas-110). |

---

## Qué resuelve

| Para el proveedor | Para el comprador |
|---|---|
| "Ayúdame a ser encontrado y conseguir nuevos negocios." | "Ayúdame a encontrar rápido proveedores confiables, compararlos y comprar mejor." |

Todo módulo debe aportar a uno de los dos. Si no, no entra.

---

## Puesta en marcha

**Requisitos:** Node ≥ 20.9 · Docker (para el stack local de Supabase).

```bash
npm install
cp .env.example .env.local
```

Levanta la base y aplica migraciones y seed:

```bash
npx supabase start && npx supabase db reset && npm run db:types
```

`supabase start` imprime la `API URL` y la `anon key`; cópialas a `.env.local` junto con la `service_role key`. Luego:

```bash
npm run dev
```

**Sin Docker**, contra un proyecto Supabase hospedado:

```bash
npx supabase link --project-ref <ref> && npx supabase db push && npm run db:types:remote
```

Usuarios de prueba del seed (contraseña `Password123`): `ana@transportesalfa.cl` (dueña), `bruno@transportesalfa.cl` (ventas), `carla@minerabeta.cl` (dueña de la compradora, además VIEWER en Alfa — valida la pertenencia múltiple).

### Comprobaciones

```bash
npm run verify && npm run db:test
```

---

## Documentación

| Documento | Contenido |
|---|---|
| **[01 · Arquitectura](docs/01-ARQUITECTURA.md)** | Dominios · stack · multiempresa · acreditación · flujo de sourcing · estrategia RLS · Storage |
| **[02 · Modelo de datos](docs/02-MODELO-DATOS.md)** | ~112 tablas documentadas · 4 diagramas ER en Mermaid · taxonomía y atributos dinámicos · índices |
| **[03 · Matching Engine](docs/03-MATCHING-ENGINE.md)** | Elegibilidad vs. scoring · 8 componentes con fórmulas · explicabilidad · Supplier Score |
| **[04 · Roadmap](docs/04-ROADMAP.md)** | MVP / V1 / V2 / V3 · orden exacto de desarrollo por fases · 20 riesgos técnicos |
| **[05 · Mejoras propuestas](docs/05-MEJORAS-PROPUESTAS.md)** | 5 correcciones al brief + 15 adiciones, priorizadas |
| **[DATABASE.md](docs/DATABASE.md)** | Referencia operativa del esquema implementado |
| **[RLS.md](docs/RLS.md)** | Matriz de acceso, helpers y decisiones de seguridad |
| **[CHANGELOG.md](CHANGELOG.md)** | Historial por fase |

---

## Las cinco decisiones que definen el sistema

1. **La oferta (`supplier_offering`), no la empresa, es la unidad atómica.** Una empresa vende decenas de servicios distintos, cada uno con su categoría, territorio, atributos y capacidad propios.
2. **Dos taxonomías ortogonales:** *qué vendes* (`taxonomy_nodes`) y *a qué industria sirves* (`industries`). Fusionarlas duplica ramas enteras del árbol.
3. **Atributos dinámicos por categoría (EAV tipado).** Cada categoría define sus propios campos y filtros sin deploy. Columnas por tipo, no `value text`, no JSON como fuente de verdad.
4. **Cotizaciones inmutables por revisión.** Nunca se sobrescribe una oferta: se agrega una revisión. La negociación y el BAFO salen gratis.
5. **RLS es la puerta, no la UI.** Un proveedor jamás puede leer la oferta de otro, en ningún estado, por ninguna vía. Probado con pgTAP en CI.

---

## Stack

**Frontend** — Next.js 15 (App Router) · React 19 · TypeScript strict · Tailwind · shadcn/ui · React Hook Form + Zod · TanStack Table
**Backend** — Supabase: PostgreSQL 15+ (`ltree`, `pg_trgm`, `unaccent`, `pg_cron`, luego `pgvector`) · Auth · Storage · RLS · Edge Functions · Realtime

---

## Estructura prevista del repositorio

```
├── docs/                        # diseño técnico (este contenido)
├── supabase/
│   ├── migrations/              # SQL forward-only, numeradas
│   ├── seed/                    # Chile: divisiones, industrias, taxonomía, atributos
│   └── tests/                   # pgTAP — RLS y reglas de negocio
├── src/
│   ├── app/
│   │   ├── (public)/            # landing, /proveedores/[slug], /discover
│   │   ├── (auth)/              # login, register, onboarding
│   │   ├── (app)/               # dashboard comprador y proveedor
│   │   └── (admin)/             # backoffice
│   ├── components/              # UI reutilizable
│   ├── server/
│   │   ├── repositories/        # único acceso a SQL
│   │   ├── services/            # reglas de negocio
│   │   ├── policies/            # autorización (defensa 2)
│   │   └── schemas/             # Zod
│   └── lib/
└── docs generados: ARCHITECTURE.md · DATABASE.md · RLS.md · FEATURES.md · CHANGELOG.md
```

---

## Próximo paso

Validar arquitectura, modelo relacional y roadmap antes de escribir la primera migración.
Ver las **cinco decisiones irreversibles** en [05-MEJORAS-PROPUESTAS.md](docs/05-MEJORAS-PROPUESTAS.md#las-cinco-que-no-se-pueden-dejar-para-después).
