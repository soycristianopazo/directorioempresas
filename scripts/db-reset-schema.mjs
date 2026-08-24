#!/usr/bin/env node
/**
 * Resetea los schemas `public` y `app` a un estado limpio. REAL, no dry-run.
 *
 * Se usa una vez al migrar del esquema anterior (Supabase Auth) al nuevo
 * (auth propia de FastAPI): ambos definen `organizations`, `profiles`, etc.
 * de forma incompatible en la capa de identidad, así que conviven mal. Antes
 * de correr esto se verificó que la base no tenía datos reales (0 usuarios,
 * 0 organizaciones) — ver CHANGELOG.md.
 *
 *   node scripts/db-reset-schema.mjs
 */

import { join } from 'node:path'
import pg from 'pg'
import dotenv from 'dotenv'

dotenv.config({ path: join(process.cwd(), '.env.local') })

const connectionString = process.env.SUPABASE_DB_URL
if (!connectionString) {
  console.error('Falta SUPABASE_DB_URL en .env.local')
  process.exit(1)
}

const client = new pg.Client({ connectionString, ssl: { rejectUnauthorized: false } })
await client.connect()

console.log('Reseteando schemas public y app...')
await client.query('drop schema if exists app cascade')
await client.query('drop schema public cascade')
await client.query('create schema public')
await client.query('grant all on schema public to postgres')
await client.query('grant usage on schema public to public')

// alembic_version vive en public y Alembic la crea sola en su primer upgrade,
// pero conviene partir sin rastro de corridas previas si las hubo.
await client.query('drop table if exists public.alembic_version')

await client.end()
console.log('✓ Esquema limpio. Ahora: cd backend && alembic upgrade head')
