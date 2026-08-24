#!/usr/bin/env node
/**
 * Aplica todas las migraciones sobre un esquema recreado desde cero y revierte.
 *
 * En PostgreSQL el DDL es transaccional, así que se puede hacer
 * `drop schema public cascade` + aplicar todo + `rollback` y dejar la base
 * exactamente como estaba. Da verificación real —¿aplica en limpio y en este
 * orden?— sin tocar nada.
 *
 * Toma un lock exclusivo durante unos segundos: correr contra desarrollo.
 *
 *   node scripts/db-dryrun-migrations.mjs
 */

import { readFile, readdir } from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import pg from 'pg'
import dotenv from 'dotenv'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
dotenv.config({ path: join(root, '.env.local') })

const SQL_DIR = join(root, 'backend', 'alembic', 'sql')

const connectionString = process.env.SUPABASE_DB_URL
if (!connectionString) {
  console.error('Falta SUPABASE_DB_URL en .env.local')
  process.exit(1)
}

const files = (await readdir(SQL_DIR)).filter((f) => f.endsWith('.sql')).sort()

const client = new pg.Client({
  connectionString,
  ssl: { rejectUnauthorized: false },
  application_name: 'dryrun-migrations',
  statement_timeout: 120_000,
})

await client.connect()

let failed = null

try {
  await client.query('begin')

  // Esquema limpio, como lo vería una instalación nueva.
  await client.query('drop schema if exists app cascade')
  await client.query('drop schema public cascade')
  await client.query('create schema public')
  await client.query('grant all on schema public to postgres')

  for (const file of files) {
    const sql = await readFile(join(SQL_DIR, file), 'utf8')
    const started = Date.now()
    try {
      await client.query(sql)
      console.log(`  ✓ ${file.padEnd(34)} ${Date.now() - started} ms`)
    } catch (error) {
      failed = { file, error }
      break
    }
  }

  if (!failed) {
    const { rows } = await client.query(`
      select
        (select count(*) from pg_tables where schemaname='public'
           and tablename not like 'audit_logs_%')                     as tablas,
        (select count(*) from pg_policies where schemaname='public')  as policies,
        (select count(*) from pg_views where schemaname='public')     as vistas,
        (select count(*) from pg_proc p join pg_namespace n
           on n.oid=p.pronamespace where n.nspname='app')             as funciones_app,
        (select count(*) from public.permissions)                     as permisos,
        (select count(*) from public.roles)                           as roles,
        (select count(*) from pg_class c join pg_namespace n
           on n.oid=c.relnamespace
           where n.nspname='public' and c.relkind in ('r','p')
             -- ENABLE, no FORCE: FORCE rompe la recursión que evitan los
             -- helpers SECURITY DEFINER — ver la nota en 0010_hardening.sql.
             and not c.relispartition and not c.relrowsecurity)       as sin_rls,
        (select count(*) from pg_roles where rolname='app_user')      as rol_app_user
    `)
    console.log('\n' + JSON.stringify(rows[0], null, 2))
  }
} finally {
  await client.query('rollback')
  await client.end()
}

if (failed) {
  console.error(`\n✗ Falló en ${failed.file}:`)
  console.error(`  ${failed.error.message}`)
  if (failed.error.hint) console.error(`  hint: ${failed.error.hint}`)
  if (failed.error.position) console.error(`  posición: ${failed.error.position}`)
  console.error('\n(la base quedó intacta: se revirtió la transacción)')
  process.exit(1)
}

console.log(`\n✓ Las ${files.length} migraciones aplican en limpio. Transacción revertida: la base no cambió.`)
