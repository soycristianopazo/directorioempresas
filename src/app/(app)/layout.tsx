import Link from 'next/link'
import { requireActiveOrg } from '@/server/auth/context'
import { can } from '@/server/policies/authorize'
import { OrganizationSwitcher } from '@/components/organization-switcher'
import { UserMenu } from '@/components/user-menu'

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const session = await requireActiveOrg()

  // Solo se listan rutas que ya existen. Catálogo, Discovery y Acreditación
  // se incorporan aquí en las fases 3, 4 y 5.
  // El tipo literal de `href` deja que typedRoutes valide cada enlace en el
  // build. Un `string` genérico desactivaría esa comprobación.
  const nav = [
    { href: '/dashboard', label: 'Panel', show: true },
    { href: '/empresa', label: 'Mi empresa', show: can(session, 'organization.read') },
    { href: '/empresa/equipo', label: 'Equipo', show: can(session, 'member.read') },
  ] as const

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="border-ink-200 dark:border-ink-800 sticky top-0 z-40 border-b bg-[var(--background)]/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-4 px-4 sm:px-6">
          <Link href="/dashboard" className="shrink-0 font-semibold tracking-tight">
            Directorio
          </Link>

          <OrganizationSwitcher
            memberships={session.memberships}
            activeOrgId={session.activeOrg.id}
          />

          <nav className="ml-auto hidden items-center gap-1 md:flex">
            {nav
              .filter((item) => item.show)
              .map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="text-ink-600 hover:bg-ink-100 hover:text-ink-900 dark:text-ink-300 dark:hover:bg-ink-800 rounded-lg px-3 py-1.5 text-sm"
                >
                  {item.label}
                </Link>
              ))}
          </nav>

          <div className="ml-auto md:ml-0">
            <UserMenu email={session.email} />
          </div>
        </div>

        {/* Navegación móvil: el proveedor trabaja desde el teléfono (§74). */}
        <nav className="border-ink-200 dark:border-ink-800 flex gap-1 overflow-x-auto border-t px-4 py-2 md:hidden">
          {nav
            .filter((item) => item.show)
            .map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="text-ink-600 hover:bg-ink-100 dark:text-ink-300 dark:hover:bg-ink-800 shrink-0 rounded-lg px-3 py-1.5 text-sm"
              >
                {item.label}
              </Link>
            ))}
        </nav>
      </header>

      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6">{children}</main>
    </div>
  )
}
