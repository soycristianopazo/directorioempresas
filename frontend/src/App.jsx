import { RouterProvider } from 'react-router-dom';
import { HelmetProvider } from 'react-helmet-async';
import { Toaster } from 'sonner';
import { AuthProvider } from '@/context/AuthContext';
import { I18nProvider } from '@/context/I18nContext';
import { router } from '@/router';

/**
 * Orden de providers, de afuera hacia adentro:
 *
 *   HelmetProvider  → gestiona el <head>; debe envolver todo lo que use <Helmet>.
 *   I18nProvider    → no depende de sesión, así que puede ir fuera de Auth.
 *   AuthProvider    → RouterProvider lo necesita disponible: ProtectedRoute
 *                     llama a useAuth() dentro de las rutas que el router monta.
 */
export default function App() {
  return (
    <HelmetProvider>
      <I18nProvider>
        <AuthProvider>
          <RouterProvider router={router} />
          <Toaster position="top-right" richColors closeButton />
        </AuthProvider>
      </I18nProvider>
    </HelmetProvider>
  );
}
