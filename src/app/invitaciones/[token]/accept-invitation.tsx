'use client'

import { useState, useTransition } from 'react'
import { useRouter } from 'next/navigation'
import { acceptInvitationAction } from '@/server/actions/team'
import { switchOrganizationAction } from '@/server/actions/organization'
import { Button } from '@/components/ui/button'

export function AcceptInvitation({ token }: { token: string }) {
  const router = useRouter()
  const [pending, startTransition] = useTransition()
  const [error, setError] = useState<string | null>(null)

  function accept() {
    setError(null)
    startTransition(async () => {
      const result = await acceptInvitationAction(token)

      if (!result.ok || !result.data) {
        setError(result.error ?? 'No se pudo aceptar la invitación')
        return
      }

      await switchOrganizationAction({ organizationId: result.data.organizationId })
      router.replace('/dashboard')
      router.refresh()
    })
  }

  return (
    <div className="space-y-3">
      <Button onClick={accept} disabled={pending} size="lg" className="w-full">
        {pending ? 'Aceptando…' : 'Aceptar invitación'}
      </Button>

      {error && (
        <p role="alert" className="text-sm text-[var(--color-danger)]">
          {error}
        </p>
      )}
    </div>
  )
}
