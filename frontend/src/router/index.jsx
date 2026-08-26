import { lazy, Suspense } from 'react';
import { createBrowserRouter } from 'react-router-dom';
import { ProtectedRoute } from '@/router/ProtectedRoute';
import { RequireOrg } from '@/router/RequireOrg';
import { RequirePlatformAdmin } from '@/router/RequirePlatformAdmin';
import { AppLayout } from '@/components/AppLayout';
import { AdminLayout } from '@/components/AdminLayout';
import { PageFallback } from '@/components/PageFallback';
import { SourcingEventLayout } from '@/components/SourcingEventLayout';

// Perezosos: cada página es su propio chunk, no parte de un bundle único de
// ~1MB que el navegador tenía que descargar y parsear antes de mostrar
// cualquier pantalla. Librerías pesadas usadas solo en algunas páginas
// (leaflet en CompanyCoveragePage, recharts en varias de sourcing/evaluación)
// dejan de pagarse en el login de alguien que nunca las visita.
const HomePage = lazy(() => import('@/pages/HomePage'));
const LoginPage = lazy(() => import('@/pages/LoginPage'));
const RegisterPage = lazy(() => import('@/pages/RegisterPage'));
const OnboardingPage = lazy(() => import('@/pages/OnboardingPage'));
const UserProfilePage = lazy(() => import('@/pages/UserProfilePage'));
const OnboardingWizardPage = lazy(() => import('@/pages/OnboardingWizardPage'));
const DashboardPage = lazy(() => import('@/pages/DashboardPage'));
const CompanyPage = lazy(() => import('@/pages/CompanyPage'));
const CompanyLocationsPage = lazy(() => import('@/pages/CompanyLocationsPage'));
const CompanyCoveragePage = lazy(() => import('@/pages/CompanyCoveragePage'));
const CatalogPage = lazy(() => import('@/pages/CatalogPage'));
const OfferingDetailPage = lazy(() => import('@/pages/OfferingDetailPage'));
const OffersPage = lazy(() => import('@/pages/OffersPage'));
const CredentialsPage = lazy(() => import('@/pages/CredentialsPage'));
const DocumentsPage = lazy(() => import('@/pages/DocumentsPage'));
const AccreditationPage = lazy(() => import('@/pages/AccreditationPage'));
const AccreditationCertificatePage = lazy(() => import('@/pages/AccreditationCertificatePage'));
const OrganizationAccreditationReviewPage = lazy(
  () => import('@/pages/organization/OrganizationAccreditationReviewPage'),
);
const SourcingEventsPage = lazy(() => import('@/pages/SourcingEventsPage'));
const SourcingOffersPage = lazy(() => import('@/pages/SourcingOffersPage'));
const SourcingEventDetailPage = lazy(() => import('@/pages/SourcingEventDetailPage'));
const SupplierInvitationsPage = lazy(() => import('@/pages/SupplierInvitationsPage'));
const MessagesPage = lazy(() => import('@/pages/MessagesPage'));
const SupplierQuotationPage = lazy(() => import('@/pages/SupplierQuotationPage'));
const MatchResultsPage = lazy(() => import('@/pages/MatchResultsPage'));
const BuyerSearchPage = lazy(() => import('@/pages/BuyerSearchPage'));
const ComparePage = lazy(() => import('@/pages/ComparePage'));
const SupplierListsPage = lazy(() => import('@/pages/SupplierListsPage'));
const EvaluationTemplatesPage = lazy(() => import('@/pages/EvaluationTemplatesPage'));
const EvaluationCommitteePage = lazy(() => import('@/pages/EvaluationCommitteePage'));
const EvaluationFormPage = lazy(() => import('@/pages/EvaluationFormPage'));
const QuotationComparatorPage = lazy(() => import('@/pages/QuotationComparatorPage'));
const NegotiationPanelPage = lazy(() => import('@/pages/NegotiationPanelPage'));
const AwardWizardPage = lazy(() => import('@/pages/AwardWizardPage'));
const AwardApprovalsPage = lazy(() => import('@/pages/AwardApprovalsPage'));
const VendorListPage = lazy(() => import('@/pages/VendorListPage'));
const SubscriptionPage = lazy(() => import('@/pages/SubscriptionPage'));
const TeamPage = lazy(() => import('@/pages/TeamPage'));
const InvitationPage = lazy(() => import('@/pages/InvitationPage'));
const AdminTaxonomyPage = lazy(() => import('@/pages/admin/AdminTaxonomyPage'));
const AdminAccreditationPage = lazy(() => import('@/pages/admin/AdminAccreditationPage'));
const NotFoundPage = lazy(() => import('@/pages/NotFoundPage'));

/** Suspense de página completa: para rutas que no viven dentro de un layout
 * persistente (AppLayout/AdminLayout ya tienen el suyo propio alrededor del
 * Outlet, así que no vuelven a pasar por acá). */
function withPageFallback(element) {
  return <Suspense fallback={<PageFallback />}>{element}</Suspense>;
}

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
  { path: '/', element: withPageFallback(<HomePage />) },
  { path: '/login', element: withPageFallback(<LoginPage />) },
  { path: '/register', element: withPageFallback(<RegisterPage />) },
  {
    element: <ProtectedRoute />,
    children: [
      { path: '/onboarding', element: withPageFallback(<OnboardingPage />) },
      { path: '/perfil', element: withPageFallback(<UserProfilePage />) },
      { path: '/invitaciones/:token', element: withPageFallback(<InvitationPage />) },
      {
        element: <RequireOrg />,
        children: [
          { path: '/onboarding/:step', element: withPageFallback(<OnboardingWizardPage />) },
          {
            element: <AppLayout />,
            children: [
              { path: '/dashboard', element: <DashboardPage /> },
              { path: '/empresa', element: <CompanyPage /> },
              { path: '/empresa/ubicaciones', element: <CompanyLocationsPage /> },
              { path: '/empresa/cobertura', element: <CompanyCoveragePage /> },
              { path: '/empresa/catalogo', element: <CatalogPage /> },
              { path: '/empresa/catalogo/:offeringId', element: <OfferingDetailPage /> },
              { path: '/empresa/ofertas', element: <OffersPage /> },
              { path: '/empresa/credenciales', element: <CredentialsPage /> },
              { path: '/empresa/documentos', element: <DocumentsPage /> },
              { path: '/empresa/acreditacion', element: <AccreditationPage /> },
              {
                path: '/empresa/acreditacion/:enrollmentId/certificado',
                element: <AccreditationCertificatePage />,
              },
              {
                path: '/empresa/acreditacion/revision',
                element: <OrganizationAccreditationReviewPage />,
              },
              { path: '/empresa/sourcing', element: <SourcingEventsPage /> },
              { path: '/empresa/ofertas', element: <SourcingOffersPage /> },
              {
                path: '/empresa/sourcing/:eventId/mi-cotizacion',
                element: <SupplierQuotationPage />,
              },
              {
                element: <SourcingEventLayout />,
                children: [
                  { path: '/empresa/sourcing/:eventId', element: <SourcingEventDetailPage /> },
                  {
                    path: '/empresa/sourcing/:eventId/resultados',
                    element: <MatchResultsPage />,
                  },
                  {
                    path: '/empresa/sourcing/:eventId/comite',
                    element: <EvaluationCommitteePage />,
                  },
                  {
                    path: '/empresa/sourcing/:eventId/evaluar',
                    element: <EvaluationFormPage />,
                  },
                  {
                    path: '/empresa/sourcing/:eventId/comparador',
                    element: <QuotationComparatorPage />,
                  },
                  {
                    path: '/empresa/sourcing/:eventId/negociacion',
                    element: <NegotiationPanelPage />,
                  },
                  {
                    path: '/empresa/sourcing/:eventId/adjudicacion',
                    element: <AwardWizardPage />,
                  },
                ],
              },
              { path: '/empresa/invitaciones', element: <SupplierInvitationsPage /> },
              { path: '/empresa/mensajes', element: <MessagesPage /> },
              { path: '/empresa/equipo', element: <TeamPage /> },
              { path: '/buscar', element: <BuyerSearchPage /> },
              { path: '/comparar', element: <ComparePage /> },
              { path: '/empresa/listas', element: <SupplierListsPage /> },
              { path: '/empresa/evaluacion/plantillas', element: <EvaluationTemplatesPage /> },
              { path: '/empresa/aprobaciones', element: <AwardApprovalsPage /> },
              { path: '/empresa/vendor-list', element: <VendorListPage /> },
              { path: '/empresa/plan', element: <SubscriptionPage /> },
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
  { path: '*', element: withPageFallback(<NotFoundPage />) },
]);
