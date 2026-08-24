#!/usr/bin/env node
/**
 * Inspección de solo lectura de la base remota.
 *
 * Se ejecuta ANTES de aplicar migraciones para detectar choques de nombres:
 * `organizations`, `profiles`, `roles` y `permissions` son nombres comunes y
 * un conflicto ahí no es trivial de deshacer.
 */

import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import pg from 'pg'
import dotenv from 'dotenv'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
dotenv.config({ path: join(root, '.env.local') })

const connectionString = process.env.SUPABASE_DB_URL
if (!connectionString) {
  console.error('Falta SUPABASE_DB_URL en .env.local')
  process.exit(1)
}

const client = new pg.Client({
  connectionString,
  ssl: { rejectUnauthorized: false },
  application_name: 'db-inspect',
})

await client.connect()

const q = async (label, sql) => {
  console.log(`\n── ${label} ──`)
  try {
    const { rows } = await client.query(sql)
    if (rows.length === 0) {
      console.log('  (vacío)')
    } else {
      for (const row of rows) console.log('  ' + Object.values(row).join(' · '))
    }
    return rows
  } catch (error) {
    // Una relación inexistente es información, no un fallo: significa que el
    // proyecto todavía no tiene ese componente.
    console.log(`  (no disponible: ${error.message})`)
    return []
  }
}

await q('Versión', `select version()`)

await q(
  'Tablas en public',
  `select tablename, coalesce(
     (select n_live_tup from pg_stat_user_tables s where s.relname = t.tablename), 0
   ) || ' filas' as filas
   from pg_tables t where schemaname = 'public' order by tablename`,
)

await q(
  'Schemas no estándar',
  `select nspname from pg_namespace
   where nspname not in ('pg_catalog','information_schema','pg_toast','public',
                         'auth','storage','graphql','graphql_public','realtime',
                         'extensions','vault','supabase_functions','supabase_migrations',
                         'pgbouncer','net','cron','_realtime','pgsodium','pgsodium_masks')
     and nspname not like 'pg_temp%' and nspname not like 'pg_toast%'
   order by nspname`,
)

await q(
  'Migraciones ya aplicadas',
  `select coalesce(string_agg(version, ', ' order by version), '(ninguna)') as versiones
   from supabase_migrations.schema_migrations`,
)

await q('Usuarios en auth.users', `select count(*) || ' usuarios' as total from auth.users`)

await q(
  'Tipos ENUM en public',
  `select typname from pg_type t
   join pg_namespace n on n.oid = t.typnamespace
   where n.nspname = 'public' and t.typtype = 'e' order by typname`,
)

await q(
  'Extensiones instaladas',
  `select extname || ' → ' || n.nspname as ext
   from pg_extension e join pg_namespace n on n.oid = e.extnamespace
   order by extname`,
)

await q(
  'Rol de conexión y privilegios',
  `select current_user || ' (superuser=' ||
     (select usesuper::text from pg_user where usename = current_user) || ')' as rol`,
)

await client.end()
console.log('\n✓ Inspección completa (solo lectura, no se modificó nada)')
