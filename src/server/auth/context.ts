import 'server-only'

import { cache } from 'react'
import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { toMemberships, type Membership } from '@/server/mappers/membership'

export const ACTIVE_ORG_COOKIE = 'active_org'

export type { Membership }

export interface SessionContext {
  userId: string
  email: string
  memberships: Membership[]
  activeOrg: Membership | null
  permissions: Set<string>
  isPlatformAdmin: boolean
}

/**
 * Contexto de sesión de la petición.
 *
 * `cache()` lo memoiza por request: varios Server Components pueden pedirlo
 * sin multiplicar consultas.
 *
 * Nota de diseño (docs/01-ARQUITECTURA.md §E.1): la organización activa vive
 * en una cookie, NO en el JWT. Por eso se revalida contra las membresías en
 * cada petición. Una cookie manipulada no concede nada: si el id no está en
 * `memberships`, se descarta.
 */
export const getSessionContext = cache(async (): Promise<SessionContext | null> => {
  const supabase = await createClient()

  const {
    data: { user },
  } = await supabase.auth.getUser()

  if (!user) return null

  const [membershipsResult, adminResult] = await Promise.all([
    supabase.from('v_my_organizations').select('*').order('joined_at', { ascending: true }),
    supabase.rpc('am_i_platform_admin'),
  ])

  const memberships = toMemberships(membershipsResult.data)

  const cookieStore = await cookies()
  const requestedOrgId = cookieStore.get(ACTIVE_ORG_COOKIE)?.value

  // Revalidación: la cookie solo se respeta si corresponde a una membresía real.
  const activeOrg = memberships.find((m) => m.id === requestedOrgId) ?? memberships[0] ?? null

  let permissions = new Set<string>()
  if (activeOrg) {
    const { data: perms } = await supabase.rpc('my_permissions', {
      p_organization_id: activeOrg.id,
    })
    if (Array.isArray(perms)) {
      permissions = new Set(perms)
    }
  }

  return {
    userId: user.id,
    email: user.email ?? '',
    memberships,
    activeOrg,
    permissions,
    isPlatformAdmin: adminResult.data === true,
  }
})

/** Exige sesión. Redirige a /login si no la hay. */
export async function requireSession(): Promise<SessionContext> {
  const ctx = await getSessionContext()
  if (!ctx) redirect('/login')
  return ctx
}

/** Exige sesión con una organización activa. Redirige al onboarding si no la hay. */
export async function requireActiveOrg(): Promise<SessionContext & { activeOrg: Membership }> {
  const ctx = await requireSession()
  if (!ctx.activeOrg) redirect('/onboarding')
  return ctx as SessionContext & { activeOrg: Membership }
}
