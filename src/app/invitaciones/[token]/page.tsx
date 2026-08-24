import type { Metadata } from 'next'
import { redirect } from 'next/navigation'
import Link from 'next/link'
import { getSessionContext } from '@/server/auth/context'
import { AcceptInvitation } from './accept-invitation'
import { Button } from '@/components/ui/button'

export const metadata: Metadata = { title: 'Invitación', robots: { index: false } }

export default async function InvitationPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params
  const session = await getSessionContext()

  // Sin sesión no se puede canjear: la invitación está atada a un correo
  // concreto y accept_invitation() lo verifica contra la sesión.
  if (!session) {
    redirect(`/login?next=${encodeURIComponent(`/invitaciones/${token}`)}`)
  }

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center px-6 py-12">
      <h1 className="text-2xl font-semibold tracking-tight">Invitación a una organización</h1>
      <p className="text-ink-500 mt-2 text-sm">
        Estás en sesión como <strong>{session.email}</strong>. La invitación solo puede aceptarse
        con la dirección a la que fue enviada.
      </p>

      <div className="mt-6">
        <AcceptInvitation token={token} />
      </div>

      <p className="text-ink-500 mt-6 text-sm">
        <Button asChild variant="link" className="px-0">
          <Link href="/dashboard">Volver al panel</Link>
        </Button>
      </p>
    </main>
  )
}
