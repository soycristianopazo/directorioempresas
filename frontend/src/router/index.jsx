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
import OnboardingWizardPage from '@/pages/OnboardingWizardPage';
import DashboardPage from '@/pages/DashboardPage';
import CompanyPage from '@/pages/CompanyPage';
import CompanyLocationsPage from '@/pages/CompanyLocationsPage';
import CompanyCoveragePage from '@/pages/CompanyCoveragePage';
import CatalogPage from '@/pages/CatalogPage';
import OfferingDetailPage from '@/pages/OfferingDetailPage';
import CredentialsPage from '@/pages/CredentialsPage';
import DocumentsPage from '@/pages/DocumentsPage';
import AccreditationPage from '@/pages/AccreditationPage';
import RequirementsPage from '@/pages/RequirementsPage';
import SourcingEventsPage from '@/pages/SourcingEventsPage';
import SourcingEventDetailPage from '@/pages/SourcingEventDetailPage';
import SupplierInvitationsPage from '@/pages/SupplierInvitationsPage';
import SupplierQuotationPage from '@/pages/SupplierQuotationPage';
import MatchResultsPage from '@/pages/MatchResultsPage';
import BuyerSearchPage from '@/pages/BuyerSearchPage';
import ComparePage from '@/pages/ComparePage';
import SupplierListsPage from '@/pages/SupplierListsPage';
import TeamPage from '@/pages/TeamPage';
import InvitationPage from '@/pages/InvitationPage';
import AdminTaxonomyPage from '@/pages/admin/AdminTaxonomyPage';
import AdminAccreditationPage from '@/pages/admin/AdminAccreditationPage';
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
          { path: '/onboarding/:step', element: <OnboardingWizardPage /> },
          {
            element: <AppLayout />,
            children: [
              { path: '/dashboard', element: <DashboardPage /> },
              { path: '/empresa', element: <CompanyPage /> },
              { path: '/empresa/ubicaciones', element: <CompanyLocationsPage /> },
              { path: '/empresa/cobertura', element: <CompanyCoveragePage /> },
              { path: '/empresa/catalogo', element: <CatalogPage /> },
              { path: '/empresa/catalogo/:offeringId', element: <OfferingDetailPage /> },
              { path: '/empresa/credenciales', element: <CredentialsPage /> },
              { path: '/empresa/documentos', element: <DocumentsPage /> },
              { path: '/empresa/acreditacion', element: <AccreditationPage /> },
              { path: '/empresa/necesidades', element: <RequirementsPage /> },
              { path: '/empresa/sourcing', element: <SourcingEventsPage /> },
              { path: '/empresa/sourcing/:eventId', element: <SourcingEventDetailPage /> },
              {
                path: '/empresa/sourcing/:eventId/resultados',
                element: <MatchResultsPage />,
              },
              {
                path: '/empresa/sourcing/:eventId/mi-cotizacion',
                element: <SupplierQuotationPage />,
              },
              { path: '/empresa/invitaciones', element: <SupplierInvitationsPage /> },
              { path: '/empresa/equipo', element: <TeamPage /> },
              { path: '/buscar', element: <BuyerSearchPage /> },
              { path: '/comparar', element: <ComparePage /> },
              { path: '/empresa/listas', element: <SupplierListsPage /> },
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
            children: [
              { path: '/admin/taxonomia', element: <AdminTaxonomyPage /> },
              { path: '/admin/acreditacion', element: <AdminAccreditationPage /> },
            ],
          },
        ],
      },
    ],
  },
  { path: '*', element: <NotFoundPage /> },
]);
