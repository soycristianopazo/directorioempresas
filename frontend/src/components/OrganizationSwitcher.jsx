import { useNavigate } from 'react-router-dom';
import { Check, ChevronsUpDown, Plus } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useAuth } from '@/context/AuthContext';
import { cn } from '@/lib/utils';

/**
 * La organización activa es una preferencia de UI (ver AuthContext y el
 * backend en organizations.switch_organization): cambiarla aquí nunca
 * concede acceso por sí sola, cada request se revalida contra la membresía
 * real. Lo interesante de este componente es que solo tiene sentido cuando
 * `memberships.length > 1` — la mayoría de las cuentas nunca lo necesitan.
 */
export function OrganizationSwitcher() {
  const { memberships, activeOrg, switchOrganization } = useAuth();
  const navigate = useNavigate();

  if (memberships.length === 0) return null;

  async function handleSelect(orgId) {
    if (orgId === activeOrg?.id) return;
    await switchOrganization(orgId);
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={cn(
          'flex h-9 max-w-56 items-center gap-2 rounded-lg border border-input px-3 text-sm',
          'hover:bg-accent',
        )}
      >
        <span className="truncate font-medium">
          {activeOrg?.trade_name ?? activeOrg?.legal_name ?? 'Organización'}
        </span>
        <ChevronsUpDown className="ml-auto size-4 shrink-0 opacity-50" />
      </DropdownMenuTrigger>

      <DropdownMenuContent align="start" className="w-64">
        <DropdownMenuLabel>Tus organizaciones</DropdownMenuLabel>
        {memberships.map((m) => (
          <DropdownMenuItem key={m.id} onSelect={() => handleSelect(m.id)}>
            <Check className={cn('size-4', m.id === activeOrg?.id ? 'opacity-100' : 'opacity-0')} />
            <span className="min-w-0 flex-1">
              <span className="block truncate">{m.trade_name ?? m.legal_name}</span>
              <span className="block truncate text-xs text-muted-foreground">
                {m.role_codes?.join(' · ') || 'Sin rol'}
              </span>
            </span>
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => navigate('/onboarding')}>
          <Plus className="size-4" />
          Registrar otra empresa
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
