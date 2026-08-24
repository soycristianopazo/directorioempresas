# Cómo se trabaja este repositorio

Dos agentes escriben aquí en paralelo: Claude Code en `backend/` y Emergent en
`frontend/`. Este documento existe para que ninguno de los dos rompa el trabajo
del otro sin querer.

---

## Frontera de responsabilidad

| Carpeta | Quién |
|---|---|
| `backend/` | Claude Code — modelos, servicios, routers, migraciones Alembic |
| `frontend/` | Emergent — componentes, páginas, estilos |
| `docs/` | Claude Code — diseño técnico, no depende del stack |
| raíz (`.github/`, `CONTRIBUTING.md`, …) | Ambos, con aviso previo |

Si alguna vez hace falta cruzar la frontera (un cambio de frontend que exige
tocar un router, o un cambio de backend que exige tocar un componente),
avisar antes en el PR y no empujar directo a `main`.

---

## El punto que sí puede doler: las migraciones

`backend/alembic/sql/` es **forward-only y numerado**. Los archivos van
`0001_foundation.sql`, `0002_auth_and_rls.sql`, … Si dos agentes generan una
`0011` al mismo tiempo sobre ramas distintas, no es un conflicto de merge
normal: es un choque de orden que puede dejar el esquema en un estado que
ninguna de las dos ramas por separado predijo.

**Regla:** solo Claude Code genera migraciones, salvo acuerdo explícito caso
a caso. Si el frontend necesita un campo o una tabla nueva, se pide en el PR
o se anota en un issue — no se improvisa un archivo `.sql` desde el otro lado.

Antes de aplicar cualquier cambio de esquema contra la base real, correr:

```bash
node scripts/db-dryrun-migrations.mjs
```

Aplica todas las migraciones dentro de una transacción y la revierte. Da
verificación real sin arriesgar los datos existentes.

---

## Ramas

- `main` — solo recibe merges vía pull request, nunca push directo.
- `feat/*` — trabajo de Claude Code.
- Rama de Emergent para su propio trabajo (el nombre lo define su flujo).

Protección de rama configurada en GitHub: *Settings → Branches → Add rule* con
"Require a pull request before merging" sobre `main`.

---

## Convenciones del stack

Ver `README.md` en la raíz para el detalle completo. Resumen:

- **Backend**: FastAPI + SQLAlchemy async + Alembic + PostgreSQL (Supabase) con
  RLS forzado. El backend conecta con el rol `app_user`, nunca con `postgres`.
- **Frontend**: CRA + Craco, JavaScript (no TypeScript), Tailwind 3.4 +
  shadcn/ui sobre Radix, React Router 7, React Hook Form + Zod, Axios.
- **Nunca `npm`** en el frontend — siempre `yarn`.
- Todas las rutas de API cuelgan de `/api`. El frontend las consume con
  `REACT_APP_BACKEND_URL` (la convención de Emergent), nunca hardcodeadas.

---

## Antes de abrir un PR

Backend:
```bash
cd backend
ruff check . && black --check . && mypy app
pytest
```

Frontend:
```bash
cd frontend
yarn lint
yarn build
```

Base de datos (si el PR toca `backend/alembic/sql/`):
```bash
node scripts/db-dryrun-migrations.mjs
```
