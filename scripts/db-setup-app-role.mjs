#!/usr/bin/env node
/**
 * Fija (o rota) la contraseña de `app_user`, el rol con el que el backend
 * conecta directamente. Se ejecuta después de aplicar la migración 0001, que
 * crea el rol pero deliberadamente sin contraseña: fijarla en el propio SQL
 * dejaría un secreto en el repositorio.
 *
 * Genera una contraseña aleatoria, la aplica con ALTER ROLE, y escribe
 * DATABASE_URL en backend/.env — que está en .gitignore. La contraseña nunca
 * se imprime en la terminal ni queda en el historial de shell más que como
 * parte de esa escritura de archivo.
 *
 *   node scripts/db-setup-app-role.mjs
 */

import { randomBytes } from 'node:crypto'
import { readFile, writeFile } from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import pg from 'pg'
import dotenv from 'dotenv'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
dotenv.config({ path: join(root, '.env.local') })

const connectionString = process.env.SUPABASE_DB_URL
if (!connectionString) {
  console.error('Falta SUPABASE_DB_URL en .env.local (conexión de administración, rol postgres).')
  process.exit(1)
}

const client = new pg.Client({ connectionString, ssl: { rejectUnauthorized: false } })
await client.connect()

const { rows } = await client.query(`select 1 from pg_roles where rolname = 'app_user'`)
if (rows.length === 0) {
  console.error('El rol app_user no existe todavía. Aplica primero la migración 0001.')
  await client.end()
  process.exit(1)
}

// Alfanumérica a propósito, por dos razones: (1) va dentro de una URL de
// conexión, y '@'/':'/'/ sin escapar rompen el parseo del DSN; (2) ALTER ROLE
// es DDL y no admite parámetros bindeados como el DML normal — el valor tiene
// que interpolarse literal en el SQL. Restringir a alfanumérico de antemano
// hace que esa interpolación sea segura sin necesitar escapar comillas.
const password = randomBytes(24).toString('base64').replace(/[^a-zA-Z0-9]/g, '').slice(0, 32)

await client.query(`alter role app_user with password '${password}'`)
await client.end()

// Host y puerto del pooler de transacciones, derivados de la URL de
// administración: mismo proyecto, mismo host, solo cambia el rol y el puerto
// (6543 transaction / 5432 session).
//
// El hostname del pooler es COMPARTIDO entre proyectos de Supabase
// (Supavisor), así que necesita el project-ref incrustado en el nombre de
// usuario para saber a qué proyecto enrutar — igual que la URL de admin trae
// `postgres.<ref>`, no `postgres` a secas. Sin ese sufijo, Supavisor responde
// "no tenant identifier provided" y rechaza la conexión antes de llegar a
// verificar ninguna contraseña.
const adminUrl = new URL(connectionString)
const poolerHost = adminUrl.hostname
const projectRef = adminUrl.username.includes('.') ? adminUrl.username.split('.')[1] : null
const pooledUsername = projectRef ? `app_user.${projectRef}` : 'app_user'
const appDatabaseUrl = `postgresql://${pooledUsername}:${password}@${poolerHost}:6543${adminUrl.pathname}`

const envPath = join(root, 'backend', '.env')
let envContent = ''
try {
  envContent = await readFile(envPath, 'utf8')
} catch {
  console.log('backend/.env no existe todavía: partiendo de backend/.env.example.')
  envContent = await readFile(join(root, 'backend', '.env.example'), 'utf8')
}

function upsertVar(content, key, value) {
  const line = `${key}=${value}`
  const pattern = new RegExp(`^${key}=.*$`, 'm')
  return pattern.test(content) ? content.replace(pattern, line) : `${content}\n${line}\n`
}

/**
 * .env.example trae JWT_SECRET vacío a propósito (es una plantilla). Si este
 * script parte de ahí porque backend/.env no existía, ese vacío pasa tal
 * cual — y un JWT_SECRET vacío hace que la app rechace arrancar (Settings
 * exige mínimo 32 caracteres). Se detecta y se genera uno real en vez de
 * dejar un .env que parece completo pero no arranca.
 */
function hasBlankJwtSecret(content) {
  const match = content.match(/^JWT_SECRET=(.*)$/m)
  return !match || match[1].trim() === ''
}

if (hasBlankJwtSecret(envContent)) {
  const jwtSecret = randomBytes(36).toString('base64url')
  envContent = upsertVar(envContent, 'JWT_SECRET', jwtSecret)
  console.log('  JWT_SECRET estaba vacío: se generó uno nuevo.')
}

envContent = upsertVar(envContent, 'DATABASE_URL', appDatabaseUrl)
envContent = upsertVar(envContent, 'MIGRATION_URL', connectionString)

await writeFile(envPath, envContent, 'utf8')

console.log('✓ Contraseña de app_user rotada y backend/.env actualizado.')
console.log(`  DATABASE_URL  → ${pooledUsername} @ ${poolerHost}:6543 (Transaction Pooler)`)
console.log(`  MIGRATION_URL → postgres @ ${poolerHost}:5432 (Session Pooler)`)
console.log('  La contraseña no se imprime aquí. Está solo en backend/.env (gitignored).')
