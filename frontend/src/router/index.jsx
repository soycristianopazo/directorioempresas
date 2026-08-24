import { createBrowserRouter } from 'react-router-dom';
import { ProtectedRoute } from '@/router/ProtectedRoute';
import { RequireOrg } from '@/router/RequireOrg';
import { AppLayout } from '@/components/AppLayout';
import HomePage from '@/pages/HomePage';
import LoginPage from '@/pages/LoginPage';
import RegisterPage from '@/pages/RegisterPage';
import OnboardingPage from '@/pages/OnboardingPage';
import DashboardPage from '@/pages/DashboardPage';
import CompanyPage from '@/pages/CompanyPage';
import TeamPage from '@/pages/TeamPage';
import InvitationPage from '@/pages/InvitationPage';
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
    ],
  },
  { path: '*', element: <NotFoundPage /> },
]);
