#!/usr/bin/env node
/**
 * Genera src/lib/supabase/database.types.ts leyendo el catálogo de Postgres.
 *
 * `supabase gen types` exige Docker incluso cuando se le pasa --db-url, porque
 * levanta pg_meta en un contenedor. Este generador habla directo con la base:
 * mismo resultado, sin depender de Docker.
 *
 * Cubre lo que este proyecto necesita: tablas, vistas, funciones, ENUMs
 * (incluidos los del schema `app`, que el generador oficial ignora al filtrar
 * por --schema public) y relaciones de clave foránea.
 *
 *   npm run db:types:remote
 */

import { writeFile } from 'node:fs/promises'
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

const OUT = join(root, 'src', 'lib', 'supabase', 'database.types.ts')

/** Mapeo de tipos de Postgres a TypeScript. */
function mapType(pgType, enumMap) {
  const isArray = pgType.startsWith('_')
  const base = isArray ? pgType.slice(1) : pgType

  let ts
  if (enumMap.has(base)) {
    ts = enumMap.get(base).tsName
  } else {
    switch (base) {
      case 'uuid':
      case 'text':
      case 'varchar':
      case 'bpchar':
      case 'char':
      case 'citext':
      case 'name':
      case 'timestamptz':
      case 'timestamp':
      case 'date':
      case 'time':
      case 'timetz':
      case 'interval':
      case 'inet':
      case 'cidr':
      case 'macaddr':
      case 'ltree':
      case 'numrange':
      case 'tsvector':
      case 'bytea':
        ts = 'string'
        break
      case 'int2':
      case 'int4':
      case 'int8':
      case 'float4':
      case 'float8':
      case 'numeric':
      case 'oid':
        ts = 'number'
        break
      case 'bool':
        ts = 'boolean'
        break
      case 'json':
      case 'jsonb':
        ts = 'Json'
        break
      case 'void':
        ts = 'undefined'
        break
      default:
        ts = 'unknown'
    }
  }

  return isArray ? `${ts}[]` : ts
}

const pascal = (s) =>
  s
    .split('_')
    .filter(Boolean)
    .map((p) => p[0].toUpperCase() + p.slice(1))
    .join('')

const client = new pg.Client({
  connectionString,
  ssl: { rejectUnauthorized: false },
  application_name: 'db-gen-types',
})

await client.connect()

// ── ENUMs ───────────────────────────────────────────────────────────────────
// Se incluyen los de cualquier schema, porque los de `app` se usan como tipos
// de columna en public y sin ellos las columnas quedarían en `unknown`.
const { rows: enumRows } = await client.query(`
  select t.typname, n.nspname,
         array_agg(e.enumlabel::text order by e.enumsortorder) as labels
  from pg_type t
  join pg_namespace n on n.oid = t.typnamespace
  join pg_enum e on e.enumtypid = t.oid
  where t.typtype = 'e' and n.nspname in ('public', 'app')
  group by t.typname, n.nspname
  order by t.typname
`)

const enumMap = new Map(
  enumRows.map((r) => [
    r.typname,
    { tsName: pascal(r.typname), labels: r.labels, schema: r.nspname },
  ]),
)

// ── Columnas de tablas y vistas ─────────────────────────────────────────────
const { rows: columns } = await client.query(`
  select c.relname            as relation,
         c.relkind            as kind,
         a.attname            as column,
         format_type(a.atttypid, null)                    as formatted,
         t.typname            as typname,
         not a.attnotnull     as nullable,
         pg_get_expr(d.adbin, d.adrelid) is not null      as has_default,
         a.attidentity <> ''                              as is_identity,
         a.attgenerated <> ''                             as is_generated,
         a.attnum
  from pg_class c
  join pg_namespace n on n.oid = c.relnamespace
  join pg_attribute a on a.attrelid = c.oid and a.attnum > 0 and not a.attisdropped
  join pg_type t on t.oid = a.atttypid
  left join pg_attrdef d on d.adrelid = c.oid and d.adnum = a.attnum
  -- Se excluyen las particiones: las de audit_logs son tablas reales pero no
  -- entidades del dominio, y siempre se accede por la tabla padre.
  where n.nspname = 'public' and c.relkind in ('r', 'p', 'v', 'm')
    and not c.relispartition
  order by c.relname, a.attnum
`)

// ── Claves foráneas (para el tipado de selects anidados) ────────────────────
const { rows: fks } = await client.query(`
  select con.conname                                        as name,
         src.relname                                        as source,
         tgt.relname                                        as target,
         (select array_agg(att.attname::text order by u.ord)
            from unnest(con.conkey) with ordinality u(attnum, ord)
            join pg_attribute att on att.attrelid = con.conrelid and att.attnum = u.attnum)
                                                            as columns,
         (select array_agg(att.attname::text order by u.ord)
            from unnest(con.confkey) with ordinality u(attnum, ord)
            join pg_attribute att on att.attrelid = con.confrelid and att.attnum = u.attnum)
                                                            as referenced
  from pg_constraint con
  join pg_class src on src.oid = con.conrelid
  join pg_class tgt on tgt.oid = con.confrelid
  join pg_namespace n on n.oid = src.relnamespace
  where con.contype = 'f' and n.nspname = 'public' and not src.relispartition
  order by src.relname, con.conname
`)

// ── Funciones invocables vía PostgREST ──────────────────────────────────────
const { rows: functions } = await client.query(`
  select p.proname                                as name,
         pg_get_function_result(p.oid)            as result,
         coalesce(p.proargnames, '{}')            as argnames,
         coalesce(
           (select array_agg(tt.typname::text order by u.ord)
              from unnest(coalesce(p.proallargtypes, p.proargtypes::oid[]))
                   with ordinality u(oid, ord)
              join pg_type tt on tt.oid = u.oid),
           '{}'
         )                                        as argtypes,
         p.pronargdefaults                        as ndefaults,
         array_length(coalesce(p.proargnames, '{}'), 1) as nargs
  from pg_proc p
  join pg_namespace n on n.oid = p.pronamespace
  where n.nspname = 'public' and p.prokind = 'f'
  order by p.proname
`)

await client.end()

// ── Emisión ─────────────────────────────────────────────────────────────────
const tables = new Map()
const views = new Map()

for (const col of columns) {
  const target = col.kind === 'v' || col.kind === 'm' ? views : tables
  if (!target.has(col.relation)) target.set(col.relation, [])
  target.get(col.relation).push(col)
}

const L = []

L.push('/**')
L.push(' * Tipos de la base de datos.')
L.push(' *')
L.push(' * ⚠️  ARCHIVO GENERADO — no editar a mano.')
L.push(' *     Regenerar con: npm run db:types:remote')
L.push(' *')
L.push(' * Generado por scripts/db-gen-types.mjs leyendo el catálogo de Postgres.')
L.push(' * No usa `supabase gen types` porque ese comando exige Docker incluso con')
L.push(' * --db-url, y además ignora los ENUMs del schema `app`.')
L.push(' */')
L.push('')
L.push(
  'export type Json = string | number | boolean | null | { [key: string]: Json | undefined } | Json[]',
)
L.push('')

for (const [name, { tsName, labels }] of [...enumMap].sort()) {
  const union = labels.map((l) => `'${l}'`)
  const oneLine = `export type ${tsName} = ${union.join(' | ')}`
  if (oneLine.length <= 100) {
    L.push(oneLine)
  } else {
    L.push(`export type ${tsName} =`)
    for (const u of union) L.push(`  | ${u}`)
  }
  void name
}
L.push('')

const relationshipsFor = (relation) => {
  const own = fks.filter((f) => f.source === relation)
  if (own.length === 0) return '      Relationships: []'
  const items = own.map(
    (f) =>
      `        {\n` +
      `          foreignKeyName: '${f.name}'\n` +
      `          columns: [${f.columns.map((c) => `'${c}'`).join(', ')}]\n` +
      `          isOneToOne: false\n` +
      `          referencedRelation: '${f.target}'\n` +
      `          referencedColumns: [${f.referenced.map((c) => `'${c}'`).join(', ')}]\n` +
      `        }`,
  )
  return `      Relationships: [\n${items.join(',\n')},\n      ]`
}

L.push('export type Database = {')
L.push('  public: {')

// Tablas
L.push('    Tables: {')
for (const [relation, cols] of [...tables].sort()) {
  L.push(`      ${relation}: {`)

  L.push('        Row: {')
  for (const c of cols) {
    L.push(`          ${c.column}: ${mapType(c.typname, enumMap)}${c.nullable ? ' | null' : ''}`)
  }
  L.push('        }')

  L.push('        Insert: {')
  for (const c of cols) {
    if (c.is_generated) continue
    const optional = c.nullable || c.has_default || c.is_identity
    L.push(
      `          ${c.column}${optional ? '?' : ''}: ${mapType(c.typname, enumMap)}${c.nullable ? ' | null' : ''}`,
    )
  }
  L.push('        }')

  L.push('        Update: {')
  for (const c of cols) {
    if (c.is_generated) continue
    L.push(`          ${c.column}?: ${mapType(c.typname, enumMap)}${c.nullable ? ' | null' : ''}`)
  }
  L.push('        }')

  L.push(relationshipsFor(relation))
  L.push('      }')
}
L.push('    }')

// Vistas
L.push('    Views: {')
for (const [relation, cols] of [...views].sort()) {
  L.push(`      ${relation}: {`)
  L.push('        Row: {')
  for (const c of cols) {
    L.push(`          ${c.column}: ${mapType(c.typname, enumMap)}${c.nullable ? ' | null' : ''}`)
  }
  L.push('        }')
  L.push(relationshipsFor(relation))
  L.push('      }')
}
L.push('    }')

// Funciones
L.push('    Functions: {')
for (const fn of functions) {
  const nargs = fn.nargs ?? 0
  const firstOptional = nargs - (fn.ndefaults ?? 0)

  L.push(`      ${fn.name}: {`)
  if (nargs === 0) {
    L.push('        Args: Record<string, never>')
  } else {
    L.push('        Args: {')
    for (let i = 0; i < nargs; i += 1) {
      const optional = i >= firstOptional
      L.push(
        `          ${fn.argnames[i]}${optional ? '?' : ''}: ${mapType(fn.argtypes[i], enumMap)}`,
      )
    }
    L.push('        }')
  }

  const result = fn.result
  let returns
  if (result === 'void') returns = 'undefined'
  else if (result.startsWith('SETOF ')) returns = `${mapType(result.slice(6), enumMap)}[]`
  else if (result.startsWith('TABLE')) returns = 'Record<string, unknown>[]'
  else returns = mapType(result.replace(/\[\]$/, ''), enumMap) + (result.endsWith('[]') ? '[]' : '')
  L.push(`        Returns: ${returns}`)
  L.push('      }')
}
L.push('    }')

// Enums y tipos compuestos
L.push('    Enums: {')
for (const [name, { tsName }] of [...enumMap].sort()) {
  L.push(`      ${name}: ${tsName}`)
}
L.push('    }')
L.push('    CompositeTypes: Record<string, never>')

L.push('  }')
L.push('}')
L.push('')
L.push("export type Tables<T extends keyof Database['public']['Tables']> =")
L.push("  Database['public']['Tables'][T]['Row']")
L.push("export type Views<T extends keyof Database['public']['Views']> =")
L.push("  Database['public']['Views'][T]['Row']")
L.push('')

await writeFile(OUT, L.join('\n'), 'utf8')

console.log(
  `✓ database.types.ts generado: ${tables.size} tablas · ${views.size} vistas · ` +
    `${functions.length} funciones · ${enumMap.size} enums · ${fks.length} FKs`,
)
