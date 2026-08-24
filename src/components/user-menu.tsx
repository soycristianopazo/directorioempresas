'use client'

import { useRouter } from 'next/navigation'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import { LogOut, User } from 'lucide-react'
import { createClient } from '@/lib/supabase/client'
import { initials } from '@/lib/utils'

export function UserMenu({ email, fullName }: { email: string; fullName?: string | null }) {
  const router = useRouter()

  async function signOut() {
    const supabase = createClient()
    await supabase.auth.signOut()
    router.replace('/login')
    router.refresh()
  }

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger
        className="bg-ink-200 text-ink-700 hover:bg-ink-300 dark:bg-ink-800 dark:text-ink-200 flex size-9 items-center justify-center rounded-full text-xs font-medium"
        aria-label="Menú de usuario"
      >
        {initials(fullName ?? email)}
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={6}
          className="border-ink-200 dark:border-ink-800 dark:bg-ink-900 z-50 min-w-56 rounded-lg border bg-white p-1 shadow-lg"
        >
          <div className="px-2 py-2">
            {fullName && <p className="truncate text-sm font-medium">{fullName}</p>}
            <p className="text-ink-500 truncate text-xs">{email}</p>
          </div>

          <DropdownMenu.Separator className="bg-ink-200 dark:bg-ink-800 my-1 h-px" />

          <DropdownMenu.Item
            onSelect={() => router.push('/perfil')}
            className="data-highlighted:bg-ink-100 dark:data-highlighted:bg-ink-800 flex cursor-pointer items-center gap-2 rounded-md px-2 py-2 text-sm outline-none"
          >
            <User className="size-4" aria-hidden />
            Mi perfil
          </DropdownMenu.Item>

          <DropdownMenu.Separator className="bg-ink-200 dark:bg-ink-800 my-1 h-px" />

          <DropdownMenu.Item
            onSelect={signOut}
            className="data-highlighted:bg-ink-100 dark:data-highlighted:bg-ink-800 flex cursor-pointer items-center gap-2 rounded-md px-2 py-2 text-sm text-[var(--color-danger)] outline-none"
          >
            <LogOut className="size-4" aria-hidden />
            Cerrar sesión
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  )
}
