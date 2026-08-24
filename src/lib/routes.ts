import type { useRouter } from 'next/navigation'

/**
 * Tipo que acepta `router.push`. Se deriva del propio router en vez de
 * importarse, para que funcione con `typedRoutes` activado o desactivado.
 */
type AppRoute = Parameters<ReturnType<typeof useRouter>['push']>[0]

/**
 * Convierte un destino que viene del usuario (típicamente `?next=`) en una
 * ruta interna segura.
 *
 * Bloquea redirecciones abiertas: `//evil.com` y `https://evil.com` son
 * destinos válidos para el navegador y llevarían al usuario fuera del sitio
 * después de iniciar sesión. Solo se acepta una ruta absoluta de un solo
 * slash inicial.
 */
export function asInternalRoute(path: string | undefined, fallback = '/dashboard'): AppRoute {
  const candidate = path?.trim()

  const isSafe =
    typeof candidate === 'string' &&
    candidate.startsWith('/') &&
    !candidate.startsWith('//') &&
    !candidate.startsWith('/\\')

  return (isSafe ? candidate : fallback) as AppRoute
}
