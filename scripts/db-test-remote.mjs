#!/usr/bin/env node
/**
 * Ejecuta la suite pgTAP contra un proyecto Supabase hospedado.
 *
 * `supabase test db` solo funciona contra el stack local (necesita Docker),
 * así que este runner hace lo mismo por conexión directa:
 *   · resuelve el `\i` de psql (que el cliente de Node no entiende)
 *   · ejecuta cada archivo .test.sql en su propia conexión
 *   · imprime la salida TAP y sale con código 1 si algo falla
 *
 * SEGURIDAD
 * ---------
 * Cada test abre `begin` y cierra con `rollback`: no deja nada escrito. Aun
 * así, apúntalo a un proyecto de DESARROLLO, nunca a producción: la suite crea
 * usuarios y organizaciones de prueba dentro de la transacción.
 *
 * La cadena de conexión se lee de SUPABASE_DB_URL (en .env.local, ignorado por
 * git). Nunca se imprime.
 *
 *   npm run db:test:remote
 */

import { readFile, readdir } from 'node:fs/promises'
import { join, dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import pg from 'pg'
import dotenv from 'dotenv'

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = resolve(__dirname, '..')
const testsDir = join(root, 'supabase', 'tests')

dotenv.config({ path: join(root, '.env.local'), quiet: true })

const connectionString = process.env.SUPABASE_DB_URL

if (!connectionString) {
  console.error(
    [
      'Falta SUPABASE_DB_URL.',
      '',
      'Añádela a .env.local (el archivo está en .gitignore):',
      '  SUPABASE_DB_URL=postgresql://postgres.<ref>:<password>@<host>:5432/postgres',
      '',
      'La encuentras en el panel de Supabase → Project Settings → Database →',
      'Connection string → URI. Usa la conexión directa (puerto 5432), no el',
      'pooler en modo transaction: pgTAP necesita sesiones completas.',
    ].join('\n'),
  )
  process.exit(1)
}

/** Resuelve los `\i ruta/archivo.sql` de psql, que node-postgres no entiende. */
async function expandIncludes(sql, depth = 0) {
  if (depth > 5) throw new Error('Demasiados niveles de \\i anidados')

  const lines = sql.split('\n')
  const out = []

  for (const line of lines) {
    const match = /^\s*\\i(?:nclude)?\s+(\S+)\s*$/.exec(line)
    if (match) {
      const included = await readFile(join(root, match[1]), 'utf8')
      out.push(await expandIncludes(included, depth + 1))
    } else {
      out.push(line)
    }
  }

  return out.join('\n')
}

function reportTap(text) {
  let failures = 0
  let assertions = 0

  for (const line of text.split('\n')) {
    const trimmed = line.trim()
    if (!trimmed) continue

    if (trimmed.startsWith('not ok')) {
      failures += 1
      assertions += 1
      console.log(`  ✗ ${trimmed}`)
    } else if (trimmed.startsWith('ok ')) {
      assertions += 1
      console.log(`  ✓ ${trimmed.replace(/^ok \d+\s*-?\s*/, '')}`)
    } else if (trimmed.startsWith('#')) {
      console.log(`  ${trimmed}`)
    } else {
      console.log(`  ${trimmed}`)
    }
  }

  return { failures, assertions }
}

async function runFile(file) {
  const raw = await readFile(join(testsDir, file), 'utf8')
  const sql = await expandIncludes(raw)

  const client = new pg.Client({
    connectionString,
    ssl: { rejectUnauthorized: false },
    application_name: 'pgtap-remote-runner',
  })

  console.log(`\n▸ ${file}`)

  await client.connect()
  try {
    const result = await client.query(sql)
    const sets = Array.isArray(result) ? result : [result]

    const text = sets
      .flatMap((r) => r?.rows ?? [])
      .map((row) => Object.values(row)[0])
      .filter((v) => typeof v === 'string')
      .join('\n')

    return reportTap(text)
  } finally {
    // El propio archivo termina con `rollback`, pero por si falló antes.
    await client.query('rollback').catch(() => {})
    await client.end()
  }
}

const files = (await readdir(testsDir)).filter((f) => f.endsWith('.test.sql')).sort()

if (files.length === 0) {
  console.error('No se encontraron archivos .test.sql en supabase/tests/')
  process.exit(1)
}

let totalFailures = 0
let totalAssertions = 0

for (const file of files) {
  try {
    const { failures, assertions } = await runFile(file)
    totalFailures += failures
    totalAssertions += assertions
  } catch (error) {
    totalFailures += 1
    console.error(`  ✗ Error ejecutando ${file}:`)
    console.error(`    ${error instanceof Error ? error.message : String(error)}`)
  }
}

console.log(
  `\n${totalFailures === 0 ? '✓' : '✗'} ${totalAssertions - totalFailures}/${totalAssertions} aserciones correctas`,
)

process.exit(totalFailures === 0 ? 0 : 1)
