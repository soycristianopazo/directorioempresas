import { Suspense, useEffect, useState } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import {
  Award,
  BadgeCheck,
  Building2,
  ChevronDown,
  ClipboardCheck,
  CreditCard,
  FileSearch,
  FileText,
  Flame,
  Gavel,
  Inbox,
  LayoutDashboard,
  List,
  ListChecks,
  MapPin,
  MapPinned,
  MessageSquare,
  Package,
  Search,
  ShieldCheck,
  Users,
} from 'lucide-react';
import { NotificationBell } from '@/components/NotificationBell';
import { OrganizationSwitcher } from '@/components/OrganizationSwitcher';
import { UserMenu } from '@/components/UserMenu';
import { FinancialTicker } from '@/components/FinancialTicker';
import { Footer } from '@/components/Footer';
import { PageFallback } from '@/components/PageFallback';
import { cn } from '@/lib/utils';
import logo from '@/assets/logo.png';

// Agrupado por Vender/Comprar, no por dominio técnico — toda empresa puede
// ejercer ambos roles a la vez, y mezclarlos (como antes, con "Acreditación"
// cargando tanto tus propias credenciales como los programas que exiges a
// tus proveedores) es lo que confundía a quien recién llega al sidebar.
const NAV_SECTIONS = [
  {
    label: null,
    items: [
      { to: '/dashboard', label: 'Panel', icon: LayoutDashboard },
      { to: '/empresa/mensajes', label: 'Chat', icon: MessageSquare },
    ],
  },
  {
    label: 'Vender',
    items: [
      { to: '/empresa', label: 'Mi empresa', icon: Building2 },
      { to: '/empresa/ubicaciones', label: 'Ubicaciones', icon: MapPin },
      { to: '/empresa/cobertura', label: 'Cobertura', icon: MapPinned },
      { to: '/empresa/catalogo', label: 'Catálogo', icon: Package },
      { to: '/empresa/ofertas', label: 'Ofertas', icon: Flame },
      {
        label: 'Acreditación',
        icon: ShieldCheck,
        children: [
          { to: '/empresa/acreditacion', label: 'Resumen', icon: ShieldCheck },
          { to: '/empresa/credenciales', label: 'Credenciales', icon: Award },
          { to: '/empresa/documentos', label: 'Documentos', icon: FileText },
        ],
      },
      // Bandeja del proveedor: invitaciones que OTRAS empresas te mandan a
      // ti para ofertar — es "vender", no "comprar" (antes vivía mal
      // ubicada bajo Comprar, confundiendo de qué lado del proceso es).
      { to: '/empresa/invitaciones', label: 'Invitaciones', icon: Inbox },
    ],
  },
  {
    label: 'Comprar',
    items: [
      { to: '/buscar', label: 'Buscar proveedores', icon: Search },
      { to: '/empresa/listas', label: 'Listas', icon: List },
      // Publicar (solo crear) y Mis ofertas (seguimiento) van separados en el
      // menú — antes vivían en una sola página y mezclaban "quiero publicar
      // algo nuevo" con "quiero ver en qué va lo que ya publiqué". Una
      // necesidad sigue sin ser un paso propio: es solo el primer campo del
      // formulario de publicación (ver SourcingEventsPage). Una sola
      // publicación, un solo ID, con match, evaluación, negociación y
      // adjudicación como pestañas de su propio workspace.
      { to: '/empresa/sourcing', label: 'Publicar', icon: FileSearch },
      { to: '/empresa/ofertas', label: 'Mis ofertas', icon: ListChecks },
      { to: '/empresa/evaluacion/plantillas', label: 'Evaluación', icon: ClipboardCheck },
      { to: '/empresa/aprobaciones', label: 'Aprobaciones', icon: Gavel },
      { to: '/empresa/vendor-list', label: 'Vendor List', icon: BadgeCheck },
      { to: '/empresa/acreditacion/revision', label: 'Revisión propia', icon: ClipboardCheck },
    ],
  },
  {
    label: 'Organización',
    items: [
      { to: '/empresa/equipo', label: 'Equipo', icon: Users },
      { to: '/empresa/plan', label: 'Plan', icon: CreditCard },
    ],
  },
];

function isNavItemActive(itemPath, currentPath) {
  if (currentPath === itemPath) return true;
  // /empresa es prefijo de todas las subrutas — solo las hojas (catálogo,
  // cobertura, etc.) heredan el resaltado de sus propias subpáginas.
  return itemPath !== '/empresa' && currentPath.startsWith(`${itemPath}/`);
}

function NavLink({ item, currentPath }) {
  const active = isNavItemActive(item.to, currentPath);
  return (
    <Link
      to={item.to}
      className={cn(
        'flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
        active
          ? 'bg-brand-teal text-white shadow-sm'
          : 'text-white/65 hover:bg-white/10 hover:text-white',
      )}
    >
      <item.icon className="size-4 shrink-0" />
      <span className="truncate">{item.label}</span>
    </Link>
  );
}

/** El grupo se abre solo si una de sus subrutas está activa — no guarda
 * preferencia del usuario porque el sidebar se remonta en cada navegación
 * completa (no hay estado que persistir entre sesiones). */
function NavGroup({ item, currentPath }) {
  const childActive = item.children.some((child) => isNavItemActive(child.to, currentPath));
  const [open, setOpen] = useState(childActive);

  useEffect(() => {
    if (childActive) setOpen(true);
  }, [childActive]);

  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
        className={cn(
          'flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
          childActive ? 'text-white' : 'text-white/65 hover:bg-white/10 hover:text-white',
        )}
      >
        <item.icon className="size-4 shrink-0" />
        <span className="flex-1 truncate text-left">{item.label}</span>
        <ChevronDown className={cn('size-3.5 shrink-0 transition-transform', open && 'rotate-180')} />
      </button>
      {open && (
        <div className="ml-3 space-y-0.5 border-l border-white/10 py-0.5 pl-3">
          {item.children.map((child) => (
            <NavLink key={child.to} item={child} currentPath={currentPath} />
          ))}
        </div>
      )}
    </div>
  );
}

function Sidebar({ currentPath }) {
  return (
    <aside className="sticky top-0 hidden h-dvh w-64 shrink-0 flex-col bg-brand-teal-dark md:flex print:hidden">
      <div className="flex h-16 shrink-0 items-center justify-center border-b border-white/10 px-5">
        <Link to="/dashboard" className="flex items-center gap-2">
          <img src={logo} alt="Directorio de Empresas" className="h-10 w-auto brightness-0 invert" />
        </Link>
      </div>

      <nav className="min-h-0 flex-1 space-y-4 overflow-y-auto px-3 py-2">
        {NAV_SECTIONS.map((section, i) => (
          <div key={section.label ?? `section-${i}`}>
            {section.label && (
              <p className="px-3 pb-1 pt-1 text-[11px] font-semibold uppercase tracking-wider text-white/40">
                {section.label}
              </p>
            )}
            <div className="space-y-0.5">
              {section.items.map((item) =>
                item.children ? (
                  <NavGroup key={item.label} item={item} currentPath={currentPath} />
                ) : (
                  <NavLink key={item.to} item={item} currentPath={currentPath} />
                ),
              )}
            </div>
          </div>
        ))}
      </nav>

      <div className="shrink-0 border-t border-white/10 p-3">
        <UserMenu variant="card" />
      </div>
    </aside>
  );
}

function MobileNav({ currentPath }) {
  const items = NAV_SECTIONS.flatMap((s) => s.items).flatMap((item) => item.children ?? [item]);
  return (
    <nav className="flex gap-1 overflow-x-auto border-t px-4 py-2 md:hidden">
      {items.map((item) => (
        <Link
          key={item.to}
          to={item.to}
          className={cn(
            'flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-muted-foreground hover:bg-accent',
            isNavItemActive(item.to, currentPath) && 'bg-accent text-accent-foreground',
          )}
        >
          <item.icon className="size-4" />
          {item.label}
        </Link>
      ))}
    </nav>
  );
}

export function AppLayout() {
  const { pathname: currentPath } = useLocation();

  return (
    <div className="flex min-h-dvh">
      <Sidebar currentPath={currentPath} />

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur print:hidden">
          <div className="flex h-16 items-center gap-3 px-4 sm:px-6">
            <Link to="/dashboard" className="shrink-0 font-semibold tracking-tight md:hidden">
              Directorio
            </Link>

            <div className="ml-auto flex shrink-0 items-center gap-3">
              <FinancialTicker />
              <OrganizationSwitcher />
              <NotificationBell />
              <div className="md:hidden">
                <UserMenu />
              </div>
            </div>
          </div>

          <MobileNav currentPath={currentPath} />
        </header>

        <main className="flex-1 px-4 py-8 sm:px-6">
          <div className="mx-auto w-full max-w-7xl">
            <Suspense fallback={<PageFallback inline />}>
              <Outlet />
            </Suspense>
          </div>
        </main>

        <Footer />
      </div>
    </div>
  );
}
