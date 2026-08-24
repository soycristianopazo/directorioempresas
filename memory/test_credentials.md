# Credenciales de prueba — Directorio de Empresas

Todas las cuentas comparten la contraseña: **`Directorio2026!`**

| Email | Rol / Contexto |
|---|---|
| ana@transportesalfa.cl | Dueña de Transportes Alfa (proveedor + comprador, perfil publicado) |
| bruno@transportesalfa.cl | Ventas en Transportes Alfa |
| carla@minerabeta.cl | Dueña de Minera Beta (comprador) + solo lectura en Transportes Alfa (multiempresa) |
| diego@ingenieriasur.cl | Proveedor Ingeniería del Sur (perfil en borrador a propósito) |

Regenerar datos: `cd /app/backend && /root/.venv/bin/python seed.py`

## Base de datos (local Postgres 15, gestionada por supervisor)
- postgres superuser: `postgres` / `postgres` @ localhost:5432/postgres (MIGRATION_URL)
- app_user (RLS): `app_user` / `appuserpass2026` @ localhost:5432/postgres (DATABASE_URL)
