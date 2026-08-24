import { createBrowserRouter } from 'react-router-dom';
import { ProtectedRoute } from '@/router/ProtectedRoute';
import { RequireOrg } from '@/router/RequireOrg';
import { RequirePlatformAdmin } from '@/router/RequirePlatformAdmin';
import { AppLayout } from '@/components/AppLayout';
import { AdminLayout } from '@/components/AdminLayout';
import HomePage from '@/pages/HomePage';
import LoginPage from '@/pages/LoginPage';
import RegisterPage from '@/pages/RegisterPage';
import OnboardingPage from '@/pages/OnboardingPage';
import DashboardPage from '@/pages/DashboardPage';
import CompanyPage from '@/pages/CompanyPage';
import TeamPage from '@/pages/TeamPage';
import InvitationPage from '@/pages/InvitationPage';
import AdminTaxonomyPage from '@/pages/admin/AdminTaxonomyPage';
import NotFoundPage from '@/pages/NotFoundPage';

/**
 * Rutas de la aplicación.
 *
 * Las páginas públicas indexables (/proveedores/:slug, /discover) NO viven
 * aquí: las sirve FastAPI con Jinja2, fuera de la SPA. Esta app cubre la
 * experiencia autenticada — dashboard, empresa, equipo — que no necesita
 * indexarse y donde una SPA no tiene el costo de SEO que tendría en una
 * página pública.
 */
export const router = createBrowserRouter([
  { path: '/', element: <HomePage /> },
  { path: '/login', element: <LoginPage /> },
  { path: '/register', element: <RegisterPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      { path: '/onboarding', element: <OnboardingPage /> },
      { path: '/invitaciones/:token', element: <InvitationPage /> },
      {
        element: <RequireOrg />,
        children: [
          {
            element: <AppLayout />,
            children: [
              { path: '/dashboard', element: <DashboardPage /> },
              { path: '/empresa', element: <CompanyPage /> },
              { path: '/empresa/equipo', element: <TeamPage /> },
            ],
          },
        ],
      },
      {
        // Hermano de RequireOrg, no anidado: un platform admin puro (cuenta
        // de backoffice) puede no pertenecer a ninguna organización.
        element: <RequirePlatformAdmin />,
        children: [
          {
            element: <AdminLayout />,
            children: [{ path: '/admin/taxonomia', element: <AdminTaxonomyPage /> }],
          },
        ],
      },
    ],
  },
  { path: '*', element: <NotFoundPage /> },
]);
