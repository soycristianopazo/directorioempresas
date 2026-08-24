'use client'

import { createBrowserClient } from '@supabase/ssr'
import { publicEnv } from '@/lib/env'
import type { Database } from './database.types'

/**
 * Cliente para el navegador.
 *
 * Reservado para lecturas públicas, Realtime y el flujo de autenticación.
 * Las escrituras de negocio van por Server Actions: así la validación con Zod
 * y la autorización de `src/server/policies` no dependen del cliente.
 */
export function createClient() {
  return createBrowserClient<Database>(
    publicEnv.NEXT_PUBLIC_SUPABASE_URL,
    publicEnv.NEXT_PUBLIC_SUPABASE_ANON_KEY,
  )
}
