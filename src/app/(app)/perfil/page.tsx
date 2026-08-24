import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { requireActiveOrg } from '@/server/auth/context'
import { createClient } from '@/lib/supabase/server'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ProfileForm } from './profile-form'

export const metadata: Metadata = { title: 'Mi perfil' }

export default async function ProfilePage() {
  const session = await requireActiveOrg()

  const supabase = await createClient()
  const { data: profile } = await supabase
    .from('profiles')
    .select('*')
    .eq('id', session.userId)
    .maybeSingle()

  if (!profile) notFound()

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Mi perfil</h1>
        <p className="text-ink-500 mt-1 text-sm">
          Tus datos personales. Son distintos de los de la empresa y te acompañan en todas las
          organizaciones a las que perteneces.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Datos personales</CardTitle>
          <CardDescription>
            Sesión iniciada como <strong>{session.email}</strong>.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ProfileForm profile={profile} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Organizaciones</CardTitle>
          <CardDescription>Empresas en las que tienes acceso.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {session.memberships.map((membership) => (
            <div
              key={membership.id}
              className="border-ink-200 dark:border-ink-800 flex flex-wrap items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm"
            >
              <span className="font-medium">{membership.displayName}</span>
              <span className="text-ink-500 text-xs">
                {membership.roleCodes.join(' · ') || 'Sin rol'}
              </span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
