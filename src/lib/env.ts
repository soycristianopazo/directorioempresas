import { z } from 'zod'

/**
 * Validación de variables de entorno al arrancar.
 *
 * Falla ruidosamente en el boot y no silenciosamente en la primera petición.
 * Un `undefined` colándose hasta el cliente de Supabase produce un error de
 * red opaco tres capas más abajo.
 */

const publicSchema = z.object({
  NEXT_PUBLIC_SUPABASE_URL: z.string().url('NEXT_PUBLIC_SUPABASE_URL debe ser una URL válida'),
  NEXT_PUBLIC_SUPABASE_ANON_KEY: z.string().min(20, 'NEXT_PUBLIC_SUPABASE_ANON_KEY es obligatoria'),
  NEXT_PUBLIC_SITE_URL: z.string().url().default('http://localhost:3000'),
})

const serverSchema = publicSchema.extend({
  SUPABASE_SERVICE_ROLE_KEY: z.string().min(20).optional(),
})

/**
 * Next.js sustituye `process.env.NEXT_PUBLIC_*` en tiempo de build solo cuando
 * se accede con la propiedad literal. Por eso no se itera sobre process.env.
 */
const rawPublic = {
  NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL,
  NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
  NEXT_PUBLIC_SITE_URL: process.env.NEXT_PUBLIC_SITE_URL,
}

function formatIssues(error: z.ZodError): string {
  return error.issues.map((i) => `  · ${i.path.join('.')}: ${i.message}`).join('\n')
}

export const publicEnv = (() => {
  const parsed = publicSchema.safeParse(rawPublic)
  if (!parsed.success) {
    throw new Error(
      `Variables de entorno públicas inválidas:\n${formatIssues(parsed.error)}\n` +
        'Copia .env.example a .env.local y complétalo.',
    )
  }
  return parsed.data
})()

/**
 * Solo invocable desde el servidor. Incluye la service_role key, que SALTA RLS.
 */
export function getServerEnv() {
  if (typeof window !== 'undefined') {
    throw new Error('getServerEnv() no puede invocarse desde el navegador')
  }

  const parsed = serverSchema.safeParse({
    ...rawPublic,
    SUPABASE_SERVICE_ROLE_KEY: process.env.SUPABASE_SERVICE_ROLE_KEY,
  })

  if (!parsed.success) {
    throw new Error(`Variables de entorno del servidor inválidas:\n${formatIssues(parsed.error)}`)
  }

  return parsed.data
}
