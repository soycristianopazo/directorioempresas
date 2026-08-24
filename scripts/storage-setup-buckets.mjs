#!/usr/bin/env node
/**
 * Crea (idempotente) los buckets de Supabase Storage que usa el backend:
 *
 *   org-media      público  — logos, banners, galerías, fotos de catálogo,
 *                             evidencia de casos de éxito. Se sirven directo
 *                             por URL pública, sin pasar por el backend.
 *   org-documents  privado  — fichas técnicas y catálogos PDF. Acceso vía
 *                             URL firmada de corta duración, emitida por el
 *                             backend tras validar el permiso correspondiente.
 *
 * Se crean por la API de Storage (POST /storage/v1/bucket), no con un INSERT
 * directo en storage.buckets: la API hace bookkeeping interno además de la
 * fila (verificado — un INSERT a mano dejaría el bucket en un estado que la
 * propia API de Storage no garantiza reconocer). Requiere las MISMAS dos
 * cabeceras que cualquier llamada a Storage con la service_role key —
 * Authorization Y apikey a la vez, ver backend/app/core/storage.py para el
 * porqué exacto.
 *
 *   node scripts/storage-setup-buckets.mjs
 */

import dotenv from 'dotenv'

dotenv.config({ path: '.env.local' })

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL
const SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY

if (!SUPABASE_URL || !SERVICE_ROLE_KEY) {
  console.error('Faltan NEXT_PUBLIC_SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY en .env.local')
  process.exit(1)
}

const headers = {
  Authorization: `Bearer ${SERVICE_ROLE_KEY}`,
  apikey: SERVICE_ROLE_KEY,
  'Content-Type': 'application/json',
}

const BUCKETS = [
  {
    id: 'org-media',
    public: true,
    file_size_limit: 8 * 1024 * 1024,
    allowed_mime_types: ['image/jpeg', 'image/png', 'image/webp', 'image/gif'],
  },
  {
    id: 'org-documents',
    public: false,
    file_size_limit: 20 * 1024 * 1024,
    allowed_mime_types: ['application/pdf'],
  },
]

async function listBuckets() {
  const res = await fetch(`${SUPABASE_URL}/storage/v1/bucket`, { headers })
  if (!res.ok) throw new Error(`No se pudo listar buckets: ${res.status} ${await res.text()}`)
  return res.json()
}

async function createBucket(bucket) {
  const res = await fetch(`${SUPABASE_URL}/storage/v1/bucket`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ name: bucket.id, ...bucket }),
  })
  if (!res.ok) throw new Error(`No se pudo crear ${bucket.id}: ${res.status} ${await res.text()}`)
}

const existing = await listBuckets()
const existingIds = new Set(existing.map((b) => b.id))

for (const bucket of BUCKETS) {
  if (existingIds.has(bucket.id)) {
    console.log(`✓ ${bucket.id} ya existe (public=${bucket.public})`)
    continue
  }
  await createBucket(bucket)
  console.log(`✓ ${bucket.id} creado (public=${bucket.public})`)
}
