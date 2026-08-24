import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';

/**
 * Puerta de las rutas privadas.
 *
 * `loading` distingue "todavía no sabemos si hay sesión" (bootstrap del
 * AuthContext, que intenta refrescar desde la cookie) de "sabemos que no hay
 * sesión". Sin esa distinción, refrescar la página en una ruta privada
 * mandaría siempre a /login durante una fracción de segundo, incluso con una
 * sesión perfectamente válida.
 */
export function ProtectedRoute() {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex min-h-dvh items-center justify-center text-sm text-muted-foreground">
        Cargando…
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  return <Outlet />;
}
