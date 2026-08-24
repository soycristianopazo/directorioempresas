# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [No publicado]

### Fase 1 — Identidad y multitenancy · 2026-08-23

**Base de datos** (9 migraciones)

- Extensiones (`ltree`, `pg_trgm`, `unaccent`, `citext`, `pgcrypto`), schema `app` no expuesto en la API, ENUMs raíz y triggers estándar.
- Validación de RUT chileno por módulo 11 **en la base**, como `CHECK`, más normalización automática al formato canónico.
- `profiles` con alta automática desde `auth.users`. Sin `organization_id`: la pertenencia es N:N.
- `organizations` con capacidades (`BUYER`/`SUPPLIER`), roles declarativos de negocio e identificadores tributarios multi-país.
- RBAC completo: 46 permisos atómicos, 14 roles de sistema, roles a medida por organización, membresías con múltiples roles.
- Invitaciones al equipo con token hasheado (SHA-256); el token nunca se almacena en claro.
- `audit_logs` particionada por mes e inmutable (revocación de UPDATE/DELETE incluso para `service_role`, más trigger).
- `domain_events` como outbox transaccional para notificaciones, analítica e integraciones.
- RLS activo en las 14 tablas, con 10 funciones helper `SECURITY DEFINER STABLE`.
- RPC transaccionales: `create_organization`, `accept_invitation`, `switch_organization`, `remove_member`.

**Aplicación**

- Next.js 16 (App Router) · React 19 · TypeScript strict · Tailwind 4 · Radix.
- Tres clientes de Supabase separados (servidor / navegador / administrativo) con `import 'server-only'` y regla de ESLint que impide saltárselos.
- Capa de servidor: `repositories` (único acceso a SQL) · `services` (negocio) · `policies` (autorización) · `schemas` (Zod) · `actions` (Server Actions).
- Autenticación: registro, login, confirmación por correo, recuperación y cambio de contraseña.
- `proxy.ts` (convención Next 16) refresca la sesión con `getUser()` —no `getSession()`— y protege las rutas privadas.
- Onboarding: alta de organización con validación de RUT en cliente y servidor.
- Selector de organización activa con revalidación server-side contra las membresías reales.
- Perfil de empresa editable, con puerta de calidad para publicar.
- Perfil personal editable.
- Gestión de equipo: listar, invitar con enlace, remover con salvaguarda de último dueño.
- Estados de carga, vacío y error; foco visible; tablas con `caption` y `scope`.

**Calidad**

- Suite pgTAP con 34 aserciones sobre seis identidades, incluida la de "competidor" que verifica el aislamiento entre organizaciones.
- CI en dos trabajos: aplicación (typecheck, lint, formato, build) y base de datos (migraciones en limpio, `db lint`, pgTAP).
- `npm run verify` para la comprobación local.

**Documentación**

- `docs/01-ARQUITECTURA.md` a `docs/05-MEJORAS-PROPUESTAS.md`: diseño técnico completo.
- `docs/DATABASE.md` y `docs/RLS.md`: referencia operativa de lo implementado.

### Decisiones cerradas

- **2026-08-23** · Dos taxonomías ortogonales: `taxonomy_nodes` (qué vendes) × `industries` (a qué industria sirves). Se descarta el árbol único del brief §7.
- **2026-08-23** · MVP acotado a supply-side + discovery. RFQ, matching y cotizaciones pasan a V1.

### Pendiente de verificación

- Las 9 migraciones y la suite pgTAP **no se han ejecutado todavía** contra una base real: el equipo de desarrollo aún no tiene Docker ni un proyecto Supabase enlazado. Typecheck, lint y build sí están verificados.
