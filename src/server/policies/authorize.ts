import 'server-only'

import { getSessionContext, type SessionContext } from '@/server/auth/context'

/**
 * Autorización a nivel de aplicación — la segunda línea de defensa.
 *
 * RLS protege FILAS. Esta capa protege OPERACIONES: una Server Action puede
 * componer varias consultas y no todas dejan rastro en una policy. Además da
 * mensajes de error decentes en vez de un resultado vacío inexplicable.
 *
 * Regla del proyecto: toda Server Action que escriba pasa por aquí antes de
 * tocar el repositorio. Nunca al revés.
 */

export class AuthorizationError extends Error {
  readonly code = 'FORBIDDEN'
  constructor(message = 'No tienes permiso para realizar esta acción') {
    super(message)
    this.name = 'AuthorizationError'
  }
}

export class AuthenticationError extends Error {
  readonly code = 'UNAUTHENTICATED'
  constructor(message = 'Debes iniciar sesión') {
    super(message)
    this.name = 'AuthenticationError'
  }
}

/** Permisos conocidos. El literal evita que un typo pase silenciosamente. */
export type Permission =
  | 'organization.read'
  | 'organization.update'
  | 'organization.delete'
  | 'organization.billing'
  | 'member.read'
  | 'member.manage'
  | 'role.manage'
  | 'audit.read'
  | 'offering.read'
  | 'offering.write'
  | 'offering.publish'
  | 'offering.delete'
  | 'document.read'
  | 'document.write'
  | 'document.delete'
  | 'accreditation.submit'
  | 'accreditation.manage'
  | 'requirement.read'
  | 'requirement.write'
  | 'sourcing_event.read'
  | 'sourcing_event.create'
  | 'sourcing_event.publish'
  | 'sourcing_event.cancel'
  | 'sourcing_event.open_bids'
  | 'quotation.read'
  | 'quotation.write'
  | 'quotation.submit'
  | 'evaluation.read'
  | 'evaluation.perform'
  | 'evaluation.manage'
  | 'negotiation.manage'
  | 'award.create'
  | 'award.approve'
  | 'contract.read'
  | 'contract.manage'
  | 'performance.review'
  | 'vendor_list.read'
  | 'vendor_list.manage'
  | 'message.send'
  | 'analytics.read'

export interface AuthorizedContext extends SessionContext {
  activeOrg: NonNullable<SessionContext['activeOrg']>
}

/** Exige sesión. Lanza en vez de redirigir: apto para Server Actions. */
export async function requireUser(): Promise<SessionContext> {
  const ctx = await getSessionContext()
  if (!ctx) throw new AuthenticationError()
  return ctx
}

/**
 * Exige sesión, organización activa y un permiso.
 *
 * @param permission  permiso requerido
 * @param organizationId  organización objetivo. Por defecto la activa.
 */
export async function authorize(
  permission: Permission,
  organizationId?: string,
): Promise<AuthorizedContext> {
  const ctx = await requireUser()

  const targetOrgId = organizationId ?? ctx.activeOrg?.id
  if (!targetOrgId) {
    throw new AuthorizationError('No hay una organización activa seleccionada')
  }

  const membership = ctx.memberships.find((m) => m.id === targetOrgId)
  if (!membership) {
    // Mismo mensaje que "sin permiso": no confirmar la existencia de la
    // organización a quien no pertenece a ella.
    throw new AuthorizationError()
  }

  // `permissions` está calculado para la organización activa. Si se pide otra,
  // hay que consultarla; se resuelve en el repositorio con has_permission.
  if (targetOrgId === ctx.activeOrg?.id) {
    if (!ctx.isPlatformAdmin && !ctx.permissions.has(permission)) {
      throw new AuthorizationError()
    }
  }

  return { ...ctx, activeOrg: membership }
}

/** Comprobación sin excepción, para condicionar la UI. */
export function can(ctx: SessionContext | null, permission: Permission): boolean {
  if (!ctx) return false
  return ctx.isPlatformAdmin || ctx.permissions.has(permission)
}

/** Exige un rol de plataforma. */
export async function authorizePlatform(): Promise<SessionContext> {
  const ctx = await requireUser()
  if (!ctx.isPlatformAdmin) throw new AuthorizationError()
  return ctx
}
