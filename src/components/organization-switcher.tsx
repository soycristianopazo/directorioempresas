'use client'

import { useState, useTransition } from 'react'
import { useRouter } from 'next/navigation'
import { Check, ChevronsUpDown, Plus } from 'lucide-react'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import { switchOrganizationAction } from '@/server/actions/organization'
import { cn } from '@/lib/utils'
import type { Membership } from '@/server/auth/context'

/**
 * Selector de organización activa.
 *
 * La organización activa es una preferencia de UI: se guarda en cookie y se
 * revalida en el servidor contra las membresías reales en cada petición
 * (docs/01-ARQUITECTURA.md §E.1). Cambiarla aquí no concede ningún acceso por
 * sí misma.
 */
export function OrganizationSwitcher({
  memberships,
  activeOrgId,
}: {
  memberships: Membership[]
  activeOrgId: string
}) {
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [pending, startTransition] = useTransition()

  const active = memberships.find((m) => m.id === activeOrgId)

  function handleSelect(organizationId: string) {
    if (organizationId === activeOrgId) return

    startTransition(async () => {
      const result = await switchOrganizationAction({ organizationId })
      if (result.ok) {
        setOpen(false)
        router.refresh()
      }
    })
  }

  if (memberships.length === 0) return null

  return (
    <DropdownMenu.Root open={open} onOpenChange={setOpen}>
      <DropdownMenu.Trigger
        disabled={pending}
        className={cn(
          'border-ink-300 flex h-9 max-w-56 min-w-0 items-center gap-2 rounded-lg border px-3 text-sm',
          'hover:bg-ink-50 dark:hover:bg-ink-800 disabled:opacity-60',
        )}
        aria-label="Cambiar de organización"
      >
        <span className="truncate">
          {active?.trade_name ?? active?.legal_name ?? 'Organización'}
        </span>
        <ChevronsUpDown className="ml-auto size-4 shrink-0 opacity-60" aria-hidden />
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="start"
          sideOffset={6}
          className="border-ink-200 dark:border-ink-800 dark:bg-ink-900 z-50 min-w-64 rounded-lg border bg-white p-1 shadow-lg"
        >
          <DropdownMenu.Label className="text-ink-500 px-2 py-1.5 text-xs font-medium">
            Tus organizaciones
          </DropdownMenu.Label>

          {memberships.map((membership) => (
            <DropdownMenu.Item
              key={membership.id}
              onSelect={() => handleSelect(membership.id)}
              className="data-highlighted:bg-ink-100 dark:data-highlighted:bg-ink-800 flex cursor-pointer items-start gap-2 rounded-md px-2 py-2 text-sm outline-none"
            >
              <Check
                className={cn(
                  'mt-0.5 size-4 shrink-0',
                  membership.id === activeOrgId ? 'opacity-100' : 'opacity-0',
                )}
                aria-hidden
              />
              <span className="min-w-0">
                <span className="block truncate">
                  {membership.trade_name ?? membership.legal_name}
                </span>
                <span className="text-ink-500 block truncate text-xs">
                  {membership.role_codes.join(' · ') || 'Sin rol'}
                </span>
              </span>
            </DropdownMenu.Item>
          ))}

          <DropdownMenu.Separator className="bg-ink-200 dark:bg-ink-800 my-1 h-px" />

          <DropdownMenu.Item
            onSelect={() => router.push('/onboarding')}
            className="data-highlighted:bg-ink-100 dark:data-highlighted:bg-ink-800 flex cursor-pointer items-center gap-2 rounded-md px-2 py-2 text-sm outline-none"
          >
            <Plus className="size-4" aria-hidden />
            Registrar otra empresa
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  )
}
