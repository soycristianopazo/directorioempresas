import { Link, Outlet, useLocation } from 'react-router-dom';
import {
  Award,
  BadgeCheck,
  Building2,
  ClipboardCheck,
  ClipboardList,
  CreditCard,
  FileSearch,
  FileText,
  Gavel,
  Inbox,
  LayoutDashboard,
  List,
  MapPinned,
  Package,
  Search,
  ShieldCheck,
  Users,
} from 'lucide-react';
import { NotificationBell } from '@/components/NotificationBell';
import { OrganizationSwitcher } from '@/components/OrganizationSwitcher';
import { UserMenu } from '@/components/UserMenu';
import { cn } from '@/lib/utils';

const NAV = [
  { to: '/dashboard', label: 'Panel', icon: LayoutDashboard },
  { to: '/empresa', label: 'Mi empresa', icon: Building2 },
  { to: '/empresa/cobertura', label: 'Cobertura', icon: MapPinned },
  { to: '/empresa/catalogo', label: 'Catálogo', icon: Package },
  { to: '/empresa/credenciales', label: 'Credenciales', icon: Award },
  { to: '/empresa/documentos', label: 'Documentos', icon: FileText },
  { to: '/empresa/acreditacion', label: 'Acreditación', icon: ShieldCheck },
  { to: '/buscar', label: 'Buscar', icon: Search },
  { to: '/empresa/listas', label: 'Listas', icon: List },
  { to: '/empresa/necesidades', label: 'Necesidades', icon: ClipboardList },
  { to: '/empresa/sourcing', label: 'Sourcing', icon: FileSearch },
  { to: '/empresa/invitaciones', label: 'Invitaciones', icon: Inbox },
  { to: '/empresa/evaluacion/plantillas', label: 'Evaluación', icon: ClipboardCheck },
  { to: '/empresa/aprobaciones', label: 'Aprobaciones', icon: Gavel },
  { to: '/empresa/vendor-list', label: 'Vendor List', icon: BadgeCheck },
  { to: '/empresa/equipo', label: 'Equipo', icon: Users },
  { to: '/empresa/plan', label: 'Plan', icon: CreditCard },
];

function isNavItemActive(itemPath, currentPath) {
  if (currentPath === itemPath) return true;
  // /empresa es prefijo de todas las subrutas — solo las hojas (catálogo,
  // cobertura, etc.) heredan el resaltado de sus propias subpáginas.
  return itemPath !== '/empresa' && currentPath.startsWith(`${itemPath}/`);
}

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

          {/* min-w-0 permite que el nav se encoja dentro del flex row y
              overflow-x-auto lo hace desplazable en vez de empujar la
              campanita/menú de usuario fuera del viewport cuando hay muchos
              items (13 y creciendo) a anchos de escritorio comunes. */}
          <nav className="ml-auto hidden min-w-0 items-center gap-1 overflow-x-auto md:flex">
            {NAV.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  'flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                  isNavItemActive(item.to, currentPath) && 'bg-accent text-accent-foreground',
                )}
              >
                <item.icon className="size-4" />
                {item.label}
              </Link>
            ))}
          </nav>

          <div className="ml-auto flex shrink-0 items-center gap-1 md:ml-0">
            <NotificationBell />
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
