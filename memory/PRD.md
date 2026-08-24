# PRD — Directorio de Empresas (Plataforma B2B de Proveedores)

## Problema
Proyecto existente traído de GitHub. Plataforma B2B chilena: Supplier Discovery +
Supplier Network + Procurement + RFQ + acreditación de proveedores. El usuario quiere
poder ver e intervenir/cambiar el proyecto.

## Arquitectura (tal como viene el repo)
- **Backend**: FastAPI (async) + SQLAlchemy 2 + asyncpg. Auth JWT (access 15m) + refresh
  token en cookie httpOnly. Seguridad multiempresa vía **Postgres Row Level Security**
  (identidad por `set_config('app.current_user_id')` con `SET LOCAL`).
  - App conecta como rol `app_user` (sujeto a RLS). Alembic migra como `postgres`.
  - Entry: `server.py` -> `app.main:app`. Rutas bajo `/api`.
- **Frontend**: React 19 (CRACO) + react-router + Tailwind + axios. `src/lib/api.js`
  usa `REACT_APP_BACKEND_URL` + `/api`, con refresh automático en 401.
- **DB**: PostgreSQL 15 local (gestionado por supervisor, conf en
  `/etc/supervisor/conf.d/postgresql.conf`). Esquema aplicado con Alembic (10 migraciones)
  que ejecutan SQL en `backend/alembic/sql/` (extensiones, ENUMs, RLS, RBAC, auditoría).
- **Nota**: También existe una implementación paralela Next.js + Supabase en la raíz
  (`src/`, `supabase/`), NO usada por el entorno Emergent. El stack activo es
  `backend/` (FastAPI) + `frontend/` (React CRACO).

## Estado actual (2026-08-24)
- ✅ Entorno levantado desde cero: Postgres instalado, roles Supabase-like creados
  (anon/authenticated/service_role), schema `extensions`, migraciones aplicadas, seed cargado.
- ✅ `.env` de backend y frontend creados; `server.py` creado para supervisor.
- ✅ Verificado E2E vía API: login, `/me` (con membresías), refresh por cookie. UI carga
  (home + login). Postgres bajo supervisor (arranca solo).

## Módulos implementados en el repo
- Identidad: registro, login, refresh, logout, /me.
- Organizaciones: crear, ver, actualizar, publicar, cambiar org activa.
- Equipo: miembros, roles, invitaciones (invitar/aceptar/revocar), multiempresa.

## Backlog / siguientes fases (docs/04-ROADMAP.md)
- Taxonomías (qué vendes × a qué industria sirves), ofertas (`supplier_offering`).
- Discovery/búsqueda, matching engine, RFQ y cotizaciones, acreditación.
