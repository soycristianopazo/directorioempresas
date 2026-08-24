/**
 * Tipos compartidos por las Server Actions.
 *
 * Viven fuera de los módulos `'use server'` porque Next.js exige que esos
 * archivos exporten únicamente funciones asíncronas.
 */
export interface ActionResult<T = undefined> {
  ok: boolean
  data?: T
  error?: string
  fieldErrors?: Record<string, string[]>
}
