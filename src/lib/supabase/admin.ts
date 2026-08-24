import 'server-only'

import { createClient as createSupabaseClient } from '@supabase/supabase-js'
import { getServerEnv } from '@/lib/env'
import type { Database } from './database.types'

/**
 * Cliente con `service_role`. SALTA RLS por completo.
 *
 * Usos legítimos, y solo estos:
 *   · jobs y workers (procesado del outbox, vencimientos, recálculo de scores)
 *   · operaciones de sistema previas a la sesión (canje de token de invitación)
 *   · backoffice de plataforma con auditoría explícita
 *
 * Nunca en una ruta que reciba input de usuario sin autorizar antes en
 * `src/server/policies`. `import 'server-only'` hace que el build falle si
 * este módulo termina en un bundle de cliente.
 */
export function createAdminClient() {
  const env = getServerEnv()

  if (!env.SUPABASE_SERVICE_ROLE_KEY) {
    throw new Error(
      'SUPABASE_SERVICE_ROLE_KEY no está configurada. Requerida para operaciones administrativas.',
    )
  }

  return createSupabaseClient<Database>(
    env.NEXT_PUBLIC_SUPABASE_URL,
    env.SUPABASE_SERVICE_ROLE_KEY,
    {
      auth: { autoRefreshToken: false, persistSession: false },
    },
  )
}
