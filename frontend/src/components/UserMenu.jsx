import { useNavigate } from 'react-router-dom';
import { ChevronsUpDown, LogOut, User } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useAuth } from '@/context/AuthContext';
import { ROLE_LABEL } from '@/lib/roleLabels';
import { cn } from '@/lib/utils';

function initials(name) {
  if (!name) return '?';
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join('');
}

/** variant="icon" (default): solo el avatar circular — usado en AdminLayout,
 * donde no hay una organización activa que dé un rol que mostrar.
 * variant="card": tarjeta ancha con avatar + nombre + rol, para el pie del
 * sidebar de AppLayout — mismo dropdown, otro disparador. */
export function UserMenu({ variant = 'icon' }) {
  const { user, activeOrg, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate('/login', { replace: true });
  }

  const roleLabel = activeOrg?.role_codes?.map((r) => ROLE_LABEL[r] ?? r).join(' · ');

  return (
    <DropdownMenu>
      {variant === 'card' ? (
        <DropdownMenuTrigger
          className={cn(
            'flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left',
            'text-white/90 hover:bg-white/10',
          )}
        >
          <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-white/15 text-xs font-medium">
            {initials(user?.full_name ?? user?.email)}
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-medium">
              {user?.full_name ?? user?.email}
            </span>
            <span className="block truncate text-xs text-white/50">
              {roleLabel || user?.email}
            </span>
          </span>
          <ChevronsUpDown className="size-4 shrink-0 text-white/40" />
        </DropdownMenuTrigger>
      ) : (
        <DropdownMenuTrigger className="flex size-9 items-center justify-center rounded-full bg-secondary text-xs font-medium text-secondary-foreground hover:opacity-90">
          {initials(user?.full_name ?? user?.email)}
        </DropdownMenuTrigger>
      )}

      <DropdownMenuContent align="end" className="w-56">
        <div className="px-2 py-1.5">
          {user?.full_name && <p className="truncate text-sm font-medium">{user.full_name}</p>}
          <p className="truncate text-xs text-muted-foreground">{user?.email}</p>
        </div>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => navigate('/perfil')}>
          <User className="size-4" />
          Mi perfil
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={handleLogout} className="text-destructive">
          <LogOut className="size-4" />
          Cerrar sesión
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
