'use server'

import { revalidatePath } from 'next/cache'
import { cookies } from 'next/headers'
import { createClient } from '@/lib/supabase/server'
import { ACTIVE_ORG_COOKIE } from '@/server/auth/context'
import { AuthorizationError } from '@/server/policies/authorize'
import * as organizationsService from '@/server/services/organizations'
import {
  createOrganizationSchema,
  switchOrganizationSchema,
  updateOrganizationSchema,
} from '@/server/schemas/organization'
import { run } from './run'
import type { ActionResult } from './types'

async function setActiveOrgCookie(organizationId: string) {
  const cookieStore = await cookies()
  cookieStore.set(ACTIVE_ORG_COOKIE, organizationId, {
    httpOnly: true,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    path: '/',
    maxAge: 60 * 60 * 24 * 365,
  })
}

export async function createOrganizationAction(
  raw: unknown,
): Promise<ActionResult<{ organizationId: string }>> {
  return run(async () => {
    const input = createOrganizationSchema.parse(raw)
    const organizationId = await organizationsService.createOrganization(input)
    await setActiveOrgCookie(organizationId)
    revalidatePath('/', 'layout')
    return { organizationId }
  })
}

export async function updateOrganizationAction(raw: unknown): Promise<ActionResult> {
  return run(async () => {
    const input = updateOrganizationSchema.parse(raw)
    await organizationsService.updateOrganization(input)
    revalidatePath('/empresa')
    revalidatePath('/dashboard')
    return undefined
  })
}

export async function publishOrganizationAction(organizationId: string): Promise<ActionResult> {
  return run(async () => {
    await organizationsService.publishOrganization(organizationId)
    revalidatePath('/', 'layout')
    return undefined
  })
}

/**
 * Cambia la organización activa.
 *
 * Escribe la cookie Y persiste la preferencia vía RPC. `switch_organization`
 * valida la membresía en la base; además getSessionContext() revalida la
 * cookie contra las membresías reales en cada petición, de modo que una cookie
 * manipulada no concede absolutamente nada.
 */
export async function switchOrganizationAction(raw: unknown): Promise<ActionResult> {
  return run(async () => {
    const { organizationId } = switchOrganizationSchema.parse(raw)

    const supabase = await createClient()
    const { error } = await supabase.rpc('switch_organization', {
      p_organization_id: organizationId,
    })
    if (error) throw new AuthorizationError('No perteneces a esa organización')

    await setActiveOrgCookie(organizationId)
    revalidatePath('/', 'layout')
    return undefined
  })
}
