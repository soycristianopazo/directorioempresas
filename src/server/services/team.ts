import 'server-only'

import { createHash, randomBytes } from 'node:crypto'
import * as membersRepo from '@/server/repositories/members'
import { authorize, AuthorizationError } from '@/server/policies/authorize'
import { publicEnv } from '@/lib/env'
import type { InviteMemberInput } from '@/server/schemas/organization'

const INVITATION_TTL_DAYS = 7

/**
 * El token viaja por correo en claro; en la base solo queda su SHA-256.
 * Si la tabla se filtra, las invitaciones pendientes siguen sin ser canjeables.
 */
function generateInvitationToken() {
  const token = randomBytes(32).toString('base64url')
  const tokenHash = createHash('sha256').update(token).digest('hex')
  return { token, tokenHash }
}

export interface InvitationResult {
  invitationId: string
  acceptUrl: string
}

export async function inviteMember(input: InviteMemberInput): Promise<InvitationResult> {
  const ctx = await authorize('member.manage', input.organizationId)

  const role = await membersRepo.findRoleByCode(input.roleCode)
  if (!role) throw new AuthorizationError('El rol indicado no existe')
  if (role.scope !== 'ORGANIZATION') {
    throw new AuthorizationError('No se puede invitar con un rol de plataforma')
  }

  const { token, tokenHash } = generateInvitationToken()
  const expiresAt = new Date(Date.now() + INVITATION_TTL_DAYS * 24 * 60 * 60 * 1000)

  const invitationId = await membersRepo.createInvitation({
    organizationId: input.organizationId,
    email: input.email,
    roleId: role.id,
    invitedBy: ctx.userId,
    tokenHash,
    expiresAt,
  })

  // El envío del correo se hará vía outbox (domain_events) en la fase 5.
  // Por ahora la URL se devuelve para copiarla a mano desde la UI.
  const acceptUrl = `${publicEnv.NEXT_PUBLIC_SITE_URL}/invitaciones/${token}`

  return { invitationId, acceptUrl }
}

export async function revokeInvitation(organizationId: string, invitationId: string) {
  await authorize('member.manage', organizationId)
  await membersRepo.revokeInvitation(invitationId)
}

export async function removeMember(organizationId: string, memberId: string) {
  await authorize('member.manage', organizationId)
  // remove_member() valida en la base que no se quede sin dueño.
  await membersRepo.removeMember(memberId)
}

export async function changeMemberRoles(
  organizationId: string,
  memberId: string,
  roleCodes: string[],
) {
  await authorize('member.manage', organizationId)

  if (roleCodes.length === 0) {
    throw new AuthorizationError('El miembro debe conservar al menos un rol')
  }

  const assignable = await membersRepo.listAssignableRoles(organizationId)
  const byCode = new Map(assignable.map((r) => [r.code, r]))

  const roleIds: string[] = []
  for (const code of roleCodes) {
    const role = byCode.get(code)
    if (!role) throw new AuthorizationError(`Rol no asignable: ${code}`)
    roleIds.push(role.id)
  }

  await membersRepo.setMemberRoles(memberId, roleIds)
}

export async function acceptInvitation(token: string): Promise<string> {
  // Sin authorize(): quien acepta todavía no pertenece a la organización.
  // La validación (token, vigencia, correo coincidente) ocurre en la base.
  return membersRepo.acceptInvitation(token)
}
