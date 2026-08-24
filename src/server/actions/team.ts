'use server'

import { revalidatePath } from 'next/cache'
import { z } from 'zod'
import * as teamService from '@/server/services/team'
import { inviteMemberSchema } from '@/server/schemas/organization'
import { run } from './run'
import type { ActionResult } from './types'

export async function inviteMemberAction(
  raw: unknown,
): Promise<ActionResult<{ acceptUrl: string }>> {
  return run(async () => {
    const input = inviteMemberSchema.parse(raw)
    const result = await teamService.inviteMember(input)
    revalidatePath('/empresa/equipo')
    return { acceptUrl: result.acceptUrl }
  })
}

const revokeSchema = z.object({
  organizationId: z.string().uuid(),
  invitationId: z.string().uuid(),
})

export async function revokeInvitationAction(raw: unknown): Promise<ActionResult> {
  return run(async () => {
    const { organizationId, invitationId } = revokeSchema.parse(raw)
    await teamService.revokeInvitation(organizationId, invitationId)
    revalidatePath('/empresa/equipo')
    return undefined
  })
}

const removeSchema = z.object({
  organizationId: z.string().uuid(),
  memberId: z.string().uuid(),
})

export async function removeMemberAction(raw: unknown): Promise<ActionResult> {
  return run(async () => {
    const { organizationId, memberId } = removeSchema.parse(raw)
    await teamService.removeMember(organizationId, memberId)
    revalidatePath('/empresa/equipo')
    return undefined
  })
}

const changeRolesSchema = z.object({
  organizationId: z.string().uuid(),
  memberId: z.string().uuid(),
  roleCodes: z.array(z.string()).min(1, 'El miembro debe conservar al menos un rol'),
})

export async function changeMemberRolesAction(raw: unknown): Promise<ActionResult> {
  return run(async () => {
    const { organizationId, memberId, roleCodes } = changeRolesSchema.parse(raw)
    await teamService.changeMemberRoles(organizationId, memberId, roleCodes)
    revalidatePath('/empresa/equipo')
    return undefined
  })
}

export async function acceptInvitationAction(
  token: string,
): Promise<ActionResult<{ organizationId: string }>> {
  return run(async () => {
    const organizationId = await teamService.acceptInvitation(token)
    revalidatePath('/', 'layout')
    return { organizationId }
  })
}
