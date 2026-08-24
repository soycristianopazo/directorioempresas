'use client'

import { useTransition } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { removeMemberAction } from '@/server/actions/team'
import { Badge, EmptyState } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { formatDate, initials } from '@/lib/utils'

interface Member {
  memberId: string
  userId: string
  status: string
  joinedAt: string
  fullName: string | null
  email: string | null
  avatarUrl: string | null
  roles: { id: string; code: string; name: string }[]
}

export function TeamTable({
  organizationId,
  members,
  canManage,
  currentUserId,
}: {
  organizationId: string
  members: Member[]
  roles: { code: string; name: string }[]
  canManage: boolean
  currentUserId: string
}) {
  const router = useRouter()
  const [pending, startTransition] = useTransition()

  function handleRemove(member: Member) {
    const label = member.fullName ?? member.email ?? 'este miembro'
    if (!window.confirm(`¿Quitar a ${label} de la organización?`)) return

    startTransition(async () => {
      const result = await removeMemberAction({ organizationId, memberId: member.memberId })
      if (result.ok) {
        toast.success('Miembro removido')
        router.refresh()
      } else {
        toast.error(result.error ?? 'No se pudo remover')
      }
    })
  }

  if (members.length === 0) {
    return (
      <div className="p-5">
        <EmptyState
          title="Todavía no hay nadie más"
          description="Invita a las personas de tu equipo que necesitan acceso."
        />
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <caption className="sr-only">Miembros de la organización</caption>
        <thead className="border-ink-200 text-ink-500 dark:border-ink-800 border-b text-left text-xs">
          <tr>
            <th scope="col" className="px-5 py-2 font-medium">
              Persona
            </th>
            <th scope="col" className="px-5 py-2 font-medium">
              Roles
            </th>
            <th scope="col" className="px-5 py-2 font-medium">
              Desde
            </th>
            {canManage && <th scope="col" className="px-5 py-2" />}
          </tr>
        </thead>
        <tbody>
          {members.map((member) => (
            <tr
              key={member.memberId}
              className="border-ink-100 dark:border-ink-800/60 border-b last:border-0"
            >
              <td className="px-5 py-3">
                <div className="flex items-center gap-3">
                  <span className="bg-ink-200 dark:bg-ink-800 flex size-8 shrink-0 items-center justify-center rounded-full text-xs font-medium">
                    {initials(member.fullName ?? member.email)}
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate font-medium">
                      {member.fullName ?? 'Sin nombre'}
                      {member.userId === currentUserId && (
                        <span className="text-ink-500 ml-2 text-xs font-normal">(tú)</span>
                      )}
                    </span>
                    {member.email && (
                      <span className="text-ink-500 block truncate text-xs">{member.email}</span>
                    )}
                  </span>
                </div>
              </td>
              <td className="px-5 py-3">
                <div className="flex flex-wrap gap-1">
                  {member.roles.length > 0 ? (
                    member.roles.map((role) => (
                      <Badge key={role.id} tone="neutral">
                        {role.name}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-ink-500 text-xs">Sin rol</span>
                  )}
                </div>
              </td>
              <td className="text-ink-500 px-5 py-3">{formatDate(member.joinedAt)}</td>
              {canManage && (
                <td className="px-5 py-3 text-right">
                  {member.userId !== currentUserId && (
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={pending}
                      onClick={() => handleRemove(member)}
                    >
                      Quitar
                    </Button>
                  )}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
