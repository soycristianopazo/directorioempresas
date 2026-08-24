import type { Metadata } from 'next'
import { notFound, redirect } from 'next/navigation'
import { requireActiveOrg } from '@/server/auth/context'
import { can } from '@/server/policies/authorize'
import * as organizationsRepo from '@/server/repositories/organizations'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { OrganizationForm } from './organization-form'
import { PublishCard } from './publish-card'

export const metadata: Metadata = { title: 'Mi empresa' }

export default async function CompanyPage() {
  const session = await requireActiveOrg()

  if (!can(session, 'organization.read')) redirect('/dashboard')

  const [organization, identifier] = await Promise.all([
    organizationsRepo.findById(session.activeOrg.id),
    organizationsRepo.getPrimaryLegalIdentifier(session.activeOrg.id),
  ])

  if (!organization) notFound()

  const canEdit = can(session, 'organization.update')

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Mi empresa</h1>
        <p className="text-ink-500 mt-1 text-sm">
          Estos datos alimentan tu perfil público y los filtros de búsqueda.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Identificación</CardTitle>
          <CardDescription>
            La razón social y el RUT solo puede modificarlos el equipo de la plataforma una vez
            verificada la empresa.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-3">
          <Detail label="Razón social" value={organization.legal_name} />
          <Detail
            label={identifier?.identifier_type ?? 'Identificación'}
            value={identifier?.value}
          />
          <Detail label="URL del perfil" value={`/proveedores/${organization.slug}`} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Perfil corporativo</CardTitle>
          <CardDescription>
            Escribe pensando en quien compra: qué haces, para quién y qué te diferencia.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <OrganizationForm organization={organization} readOnly={!canEdit} />
        </CardContent>
      </Card>

      {canEdit && <PublishCard organizationId={organization.id} status={organization.status} />}
    </div>
  )
}

function Detail({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <dt className="text-ink-500 text-xs">{label}</dt>
      <dd className="mt-0.5 text-sm font-medium">{value ?? '—'}</dd>
    </div>
  )
}
