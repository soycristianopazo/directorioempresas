import { Link } from 'react-router-dom';
import { Outlet } from 'react-router-dom';
import { UserMenu } from '@/components/UserMenu';
import { Badge } from '@/components/ui/badge';
import logo from '@/assets/logo.png';

/**
 * Layout propio del backoffice de plataforma — no reutiliza AppLayout, que
 * asume una organización activa (OrganizationSwitcher) que un platform admin
 * puro puede no tener.
 *
 * Único lugar fuera de la landing donde aparece un acento de la paleta de
 * marca (bg-brand-teal-dark en el badge): decorativo, igual que el logo —
 * el resto de la pantalla (tablas, formularios, botones) usa tokens sober,
 * mismo criterio que TeamPage/CompanyPage.
 */
export function AdminLayout() {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-3 px-4 sm:px-6">
          <Link to="/dashboard" className="flex shrink-0 items-center gap-2">
            <img src={logo} alt="Directorio de Empresas" className="h-6 w-auto" />
          </Link>
          <Badge className="bg-brand-teal-dark text-white hover:bg-brand-teal-dark">
            Backoffice
          </Badge>

          <div className="ml-auto">
            <UserMenu />
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6">
        <Outlet />
      </main>
    </div>
  );
}
