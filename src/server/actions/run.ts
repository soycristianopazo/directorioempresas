import 'server-only'

import { z } from 'zod'
import { AuthenticationError, AuthorizationError } from '@/server/policies/authorize'
import type { ActionResult } from './types'

/**
 * Envoltorio común de Server Actions.
 *
 * Traduce excepciones a un resultado serializable y no filtra detalles
 * internos al cliente: un error inesperado se registra en el servidor y al
 * usuario le llega un mensaje genérico. Los errores de negocio que la propia
 * base levanta con `raise exception` sí se propagan, porque están escritos
 * para ser leídos por una persona.
 */
export async function run<T>(fn: () => Promise<T>): Promise<ActionResult<T>> {
  try {
    const data = await fn()
    return { ok: true, data }
  } catch (error) {
    if (error instanceof z.ZodError) {
      return {
        ok: false,
        error: 'Revisa los datos del formulario',
        fieldErrors: z.flattenError(error).fieldErrors as Record<string, string[]>,
      }
    }

    if (error instanceof AuthenticationError || error instanceof AuthorizationError) {
      return { ok: false, error: error.message }
    }

    if (error instanceof Error && isDomainMessage(error.message)) {
      return { ok: false, error: error.message }
    }

    console.error('[action] error inesperado', error)
    return { ok: false, error: 'Ocurrió un error inesperado. Intenta nuevamente.' }
  }
}

/**
 * Heurística para distinguir un mensaje escrito para el usuario (los
 * `raise exception` de las migraciones, en español y con mayúscula inicial)
 * de un error técnico que no debe salir del servidor.
 */
function isDomainMessage(message: string): boolean {
  if (message.length > 200) return false
  if (/[A-Z]{2,}_[A-Z]/.test(message)) return false // ERRCODE, nombres internos
  return /^[A-ZÁÉÍÓÚÑ]/.test(message)
}
