import type { Metadata } from 'next'
import { redirect } from 'next/navigation'
import { requireActiveOrg } from '@/server/auth/context'
import { can } from '@/server/policies/authorize'
import * as membersRepo from '@/server/repositories/members'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { TeamTable } from './team-table'
import { InviteMemberForm } from './invite-member-form'

export const metadata: Metadata = { title: 'Equipo' }

export default async function TeamPage() {
  const session = await requireActiveOrg()

  if (!can(session, 'member.read')) redirect('/dashboard')

  const organizationId = session.activeOrg.id
  const canManage = can(session, 'member.manage')

  const [team, roles, invitations] = await Promise.all([
    membersRepo.listTeam(organizationId),
    membersRepo.listAssignableRoles(organizationId),
    canManage ? membersRepo.listPendingInvitations(organizationId) : Promise.resolve([]),
  ])

  // El correo vive en auth.users y requiere el cliente administrativo.
  // Solo se resuelve para quien puede administrar el equipo.
  let emails = new Map<string, string>()
  if (canManage) {
    try {
      emails = await membersRepo.resolveEmails(team.map((m) => m.userId))
    } catch {
      // Sin SUPABASE_SERVICE_ROLE_KEY configurada la pantalla sigue siendo útil.
    }
  }

  const teamWithEmails = team.map((member) => ({
    ...member,
    email: emails.get(member.userId) ?? null,
  }))

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Equipo</h1>
        <p className="text-ink-500 mt-1 text-sm">
          Personas con acceso a {session.activeOrg.trade_name ?? session.activeOrg.legal_name}.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Miembros ({teamWithEmails.length})</CardTitle>
          <CardDescription>
            Cada persona puede tener varios roles. Los permisos son la suma de todos ellos.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <TeamTable
            organizationId={organizationId}
            members={teamWithEmails}
            roles={roles.map((r) => ({ code: r.code, name: r.name }))}
            canManage={canManage}
            currentUserId={session.userId}
          />
        </CardContent>
      </Card>

      {canManage && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Invitar a alguien</CardTitle>
              <CardDescription>
                La invitación vence en 7 días y solo puede aceptarla el correo indicado.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <InviteMemberForm
                organizationId={organizationId}
                roles={roles.map((r) => ({ code: r.code, name: r.name }))}
              />
            </CardContent>
          </Card>

          {invitations.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Invitaciones pendientes ({invitations.length})</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {invitations.map((invitation) => {
                  const role = invitation.roles as unknown as { name: string } | null
                  return (
                    <div
                      key={invitation.id}
                      className="border-ink-200 dark:border-ink-800 flex flex-wrap items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm"
                    >
                      <span>{invitation.email}</span>
                      <span className="text-ink-500 text-xs">
                        {role?.name ?? '—'} · vence{' '}
                        {new Intl.DateTimeFormat('es-CL', { dateStyle: 'medium' }).format(
                          new Date(invitation.expires_at),
                        )}
                      </span>
                    </div>
                  )
                })}
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
