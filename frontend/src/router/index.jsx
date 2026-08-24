import { createBrowserRouter } from 'react-router-dom';
import { ProtectedRoute } from '@/router/ProtectedRoute';
import HomePage from '@/pages/HomePage';
import LoginPage from '@/pages/LoginPage';
import RegisterPage from '@/pages/RegisterPage';
import DashboardPage from '@/pages/DashboardPage';
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
    children: [{ path: '/dashboard', element: <DashboardPage /> }],
  },
  { path: '*', element: <NotFoundPage /> },
]);
