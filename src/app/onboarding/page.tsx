import type { Metadata } from 'next'
import { redirect } from 'next/navigation'
import { requireSession } from '@/server/auth/context'
import { CreateOrganizationForm } from './create-organization-form'

export const metadata: Metadata = { title: 'Registra tu empresa' }

export default async function OnboardingPage() {
  const session = await requireSession()

  // Si ya pertenece a alguna organización, el onboarding está cumplido.
  if (session.memberships.length > 0) redirect('/dashboard')

  return (
    <main className="mx-auto flex min-h-dvh max-w-lg flex-col justify-center px-6 py-12">
      <div className="mb-8 space-y-1">
        <p className="text-brand-600 text-sm font-medium">Paso 1 de 8</p>
        <h1 className="text-2xl font-semibold tracking-tight">Registra tu empresa</h1>
        <p className="text-ink-500 text-sm">
          Con estos datos creamos tu organización. Después completarás industrias, catálogo,
          cobertura y acreditación.
        </p>
      </div>

      <CreateOrganizationForm />
    </main>
  )
}
