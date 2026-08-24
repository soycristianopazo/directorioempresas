import type { NextRequest } from 'next/server'
import { updateSession } from '@/lib/supabase/middleware'

/**
 * Convención `proxy` de Next 16 (antes `middleware`).
 *
 * Refresca la sesión de Supabase en cada petición y protege las rutas
 * privadas. La lógica vive en src/lib/supabase/middleware.ts.
 */
export default async function proxy(request: NextRequest) {
  return updateSession(request)
}

export const config = {
  matcher: [
    /*
     * Todas las rutas excepto assets estáticos y el favicon. El proxy refresca
     * la sesión, así que debe correr en las rutas de página; excluir imágenes
     * y fuentes evita trabajo inútil en cada asset.
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|avif|ico|woff2?)$).*)',
  ],
}
