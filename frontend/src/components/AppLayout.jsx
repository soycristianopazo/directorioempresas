import { Link, Outlet, useLocation } from 'react-router-dom';
import { Building2, LayoutDashboard, Users } from 'lucide-react';
import { OrganizationSwitcher } from '@/components/OrganizationSwitcher';
import { UserMenu } from '@/components/UserMenu';
import { cn } from '@/lib/utils';

const NAV = [
  { to: '/dashboard', label: 'Panel', icon: LayoutDashboard },
  { to: '/empresa', label: 'Mi empresa', icon: Building2 },
  { to: '/empresa/equipo', label: 'Equipo', icon: Users },
];

export function AppLayout() {
  const { pathname: currentPath } = useLocation();

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-4 px-4 sm:px-6">
          <Link to="/dashboard" className="shrink-0 font-semibold tracking-tight">
            Directorio
          </Link>

          <OrganizationSwitcher />

          <nav className="ml-auto hidden items-center gap-1 md:flex">
            {NAV.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  'flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                  currentPath === item.to && 'bg-accent text-accent-foreground',
                )}
              >
                <item.icon className="size-4" />
                {item.label}
              </Link>
            ))}
          </nav>

          <div className="ml-auto md:ml-0">
            <UserMenu />
          </div>
        </div>

        {/* Navegación móvil: el proveedor gestiona su perfil desde el teléfono. */}
        <nav className="flex gap-1 overflow-x-auto border-t px-4 py-2 md:hidden">
          {NAV.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className="flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-muted-foreground hover:bg-accent"
            >
              <item.icon className="size-4" />
              {item.label}
            </Link>
          ))}
        </nav>
      </header>

      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6">
        <Outlet />
      </main>
    </div>
  );
}
