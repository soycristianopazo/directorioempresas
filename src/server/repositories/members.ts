import 'server-only'

import { createClient } from '@/lib/supabase/server'
import { createAdminClient } from '@/lib/supabase/admin'
import type { Tables } from '@/lib/supabase/database.types'

export type Role = Tables<'roles'>

export interface TeamMember {
  memberId: string
  userId: string
  status: string
  joinedAt: string
  fullName: string | null
  email: string | null
  avatarUrl: string | null
  roles: { id: string; code: string; name: string }[]
}

export async function listTeam(organizationId: string): Promise<TeamMember[]> {
  const supabase = await createClient()

  const { data, error } = await supabase
    .from('organization_members')
    .select(
      `id, user_id, status, joined_at,
       profiles:profiles!organization_members_user_id_fkey ( full_name, avatar_url ),
       member_roles ( roles ( id, code, name ) )`,
    )
    .eq('organization_id', organizationId)
    .neq('status', 'REMOVED')
    .order('joined_at', { ascending: true })

  if (error) throw error

  type Row = {
    id: string
    user_id: string
    status: string
    joined_at: string
    profiles: { full_name: string | null; avatar_url: string | null } | null
    member_roles: { roles: { id: string; code: string; name: string } | null }[] | null
  }

  return ((data ?? []) as unknown as Row[]).map((row) => ({
    memberId: row.id,
    userId: row.user_id,
    status: row.status,
    joinedAt: row.joined_at,
    fullName: row.profiles?.full_name ?? null,
    // El email vive en auth.users y no es legible con la clave anónima.
    // Se resuelve aparte solo cuando la pantalla lo necesita.
    email: null,
    avatarUrl: row.profiles?.avatar_url ?? null,
    roles: (row.member_roles ?? [])
      .map((mr) => mr.roles)
      .filter((r): r is { id: string; code: string; name: string } => r !== null),
  }))
}

/** Roles asignables: los de sistema con ámbito de organización + los custom. */
export async function listAssignableRoles(organizationId: string): Promise<Role[]> {
  const supabase = await createClient()

  const { data, error } = await supabase
    .from('roles')
    .select('*')
    .eq('scope', 'ORGANIZATION')
    .or(`organization_id.is.null,organization_id.eq.${organizationId}`)
    .order('sort_order', { ascending: true })

  if (error) throw error
  return data ?? []
}

export async function findRoleByCode(code: string): Promise<Role | null> {
  const supabase = await createClient()
  const { data, error } = await supabase
    .from('roles')
    .select('*')
    .eq('code', code)
    .is('organization_id', null)
    .maybeSingle()

  if (error) throw error
  return data
}

export interface CreateInvitationParams {
  organizationId: string
  email: string
  roleId: string
  invitedBy: string
  tokenHash: string
  expiresAt: Date
}

export async function createInvitation(params: CreateInvitationParams): Promise<string> {
  const supabase = await createClient()

  // Reemplaza cualquier invitación pendiente previa al mismo correo: el índice
  // parcial org_invitations_pending_key solo admite una.
  await supabase
    .from('organization_invitations')
    .update({ status: 'REVOKED', revoked_at: new Date().toISOString() })
    .eq('organization_id', params.organizationId)
    .eq('email', params.email)
    .eq('status', 'PENDING')

  const { data, error } = await supabase
    .from('organization_invitations')
    .insert({
      organization_id: params.organizationId,
      email: params.email,
      role_id: params.roleId,
      token_hash: params.tokenHash,
      invited_by: params.invitedBy,
      expires_at: params.expiresAt.toISOString(),
    })
    .select('id')
    .single()

  if (error) throw error
  return data.id
}

export async function listPendingInvitations(organizationId: string) {
  const supabase = await createClient()

  const { data, error } = await supabase
    .from('organization_invitations')
    .select('id, email, expires_at, created_at, roles ( code, name )')
    .eq('organization_id', organizationId)
    .eq('status', 'PENDING')
    .order('created_at', { ascending: false })

  if (error) throw error
  return data ?? []
}

export async function revokeInvitation(invitationId: string): Promise<void> {
  const supabase = await createClient()

  const { error } = await supabase
    .from('organization_invitations')
    .update({ status: 'REVOKED', revoked_at: new Date().toISOString() })
    .eq('id', invitationId)
    .eq('status', 'PENDING')

  if (error) throw error
}

/**
 * Canjea el token de invitación.
 *
 * Corre como el usuario autenticado: accept_invitation() es SECURITY DEFINER y
 * valida internamente que el correo de la sesión coincide con el invitado.
 */
export async function acceptInvitation(token: string): Promise<string> {
  const supabase = await createClient()

  const { data, error } = await supabase.rpc('accept_invitation', { p_token: token })

  if (error) throw error
  if (!data) throw new Error('accept_invitation no devolvió la organización')
  return data
}

export async function removeMember(memberId: string): Promise<void> {
  const supabase = await createClient()
  const { error } = await supabase.rpc('remove_member', { p_member_id: memberId })
  if (error) throw error
}

export async function setMemberRoles(memberId: string, roleIds: string[]): Promise<void> {
  const supabase = await createClient()

  const { error: deleteError } = await supabase
    .from('member_roles')
    .delete()
    .eq('member_id', memberId)

  if (deleteError) throw deleteError

  if (roleIds.length === 0) return

  const { error } = await supabase
    .from('member_roles')
    .insert(roleIds.map((roleId) => ({ member_id: memberId, role_id: roleId })))

  if (error) throw error
}

/**
 * Resuelve emails de los miembros del equipo.
 *
 * auth.users no es accesible con la clave anónima, así que requiere el cliente
 * administrativo. Se llama SOLO desde la pantalla de equipo y después de haber
 * autorizado `member.read`: nunca con ids que no vengan de listTeam().
 */
export async function resolveEmails(userIds: string[]): Promise<Map<string, string>> {
  if (userIds.length === 0) return new Map()

  const admin = createAdminClient()
  const result = new Map<string, string>()

  const { data, error } = await admin.auth.admin.listUsers({ page: 1, perPage: 1000 })
  if (error) throw error

  const wanted = new Set(userIds)
  for (const user of data.users) {
    if (wanted.has(user.id) && user.email) {
      result.set(user.id, user.email)
    }
  }

  return result
}
