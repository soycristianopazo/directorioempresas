import type { Metadata } from 'next'
import Link from 'next/link'
import { requireActiveOrg } from '@/server/auth/context'
import {
  Badge,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export const metadata: Metadata = { title: 'Panel' }

export default async function DashboardPage() {
  const session = await requireActiveOrg()
  const org = session.activeOrg
  const capabilities = new Set(org.capabilities)

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{org.displayName}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <Badge tone={org.status === 'ACTIVE' ? 'success' : 'warning'}>
              {org.status === 'ACTIVE' ? 'Perfil publicado' : 'Perfil en borrador'}
            </Badge>
            {[...capabilities].map((capability) => (
              <Badge key={capability} tone="brand">
                {capability === 'BUYER' ? 'Comprador' : 'Proveedor'}
              </Badge>
            ))}
            <span className="text-ink-500 text-xs">
              Tu rol: {org.roleCodes.join(', ') || 'sin rol asignado'}
            </span>
          </div>
        </div>

        {org.status !== 'ACTIVE' && (
          <Button asChild>
            <Link href="/empresa">Completar perfil</Link>
          </Button>
        )}
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Completitud del perfil</CardTitle>
          <CardDescription>
            Un perfil completo aparece en más búsquedas y califica para más oportunidades.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-semibold tabular-nums">{org.completionPct}%</span>
            <span className="text-ink-500 text-sm">completado</span>
          </div>
          <div
            className="bg-ink-200 dark:bg-ink-800 h-2 w-full overflow-hidden rounded-full"
            role="progressbar"
            aria-valuenow={org.completionPct}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Completitud del perfil"
          >
            <div
              className="bg-brand-600 h-full rounded-full transition-[width]"
              style={{ width: `${org.completionPct}%` }}
            />
          </div>
          <p className="text-ink-500 text-sm">
            El cálculo por secciones —identificación, catálogo, cobertura, experiencia y
            acreditación— se activa en la fase 3.
          </p>
        </CardContent>
      </Card>

      <section className="grid gap-4 sm:grid-cols-2">
        {capabilities.has('SUPPLIER') && (
          <Card>
            <CardHeader>
              <CardTitle>Como proveedor</CardTitle>
              <CardDescription>Haz que te encuentren.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <NextStep label="Completar datos de la empresa" href="/empresa" />
              <NextStep label="Publicar productos y servicios" phase="Fase 3" />
              <NextStep label="Definir cobertura territorial" phase="Fase 3" />
              <NextStep label="Iniciar acreditación" phase="Fase 5" />
            </CardContent>
          </Card>
        )}

        {capabilities.has('BUYER') && (
          <Card>
            <CardHeader>
              <CardTitle>Como comprador</CardTitle>
              <CardDescription>Encuentra y compara proveedores.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <NextStep label="Invitar a tu equipo" href="/empresa/equipo" />
              <NextStep label="Buscar proveedores" phase="Fase 4" />
              <NextStep label="Crear tu lista de proveedores" phase="Fase 4" />
            </CardContent>
          </Card>
        )}
      </section>

      <p className="text-ink-500 text-sm">
        Catálogo, búsqueda, acreditación y cotizaciones llegan en las fases 3 a 7 del roadmap.
      </p>
    </div>
  )
}

/**
 * Paso siguiente. Sin `href` se muestra deshabilitado con la fase en la que
 * llega: es preferible a un enlace que lleva a un 404.
 */
function NextStep({
  label,
  href,
  phase,
}: {
  label: string
  href?: '/empresa' | '/empresa/equipo'
  phase?: string
}) {
  const bullet = (
    <span aria-hidden className="border-ink-300 size-4 shrink-0 rounded-full border-2" />
  )

  if (!href) {
    return (
      <div className="text-ink-400 flex items-center gap-2 px-2 py-1.5">
        {bullet}
        <span>{label}</span>
        {phase && <Badge tone="neutral">{phase}</Badge>}
      </div>
    )
  }

  return (
    <Link
      href={href}
      className="hover:bg-ink-50 dark:hover:bg-ink-800 flex items-center gap-2 rounded-md px-2 py-1.5"
    >
      {bullet}
      <span>{label}</span>
    </Link>
  )
}
