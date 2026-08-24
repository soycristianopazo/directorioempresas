import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';

/**
 * Exige que el usuario autenticado tenga al menos una organización.
 *
 * Va DENTRO de ProtectedRoute (que ya exige sesión): aquí solo falta decidir
 * qué hacer cuando la sesión es válida pero la cuenta todavía no tiene
 * empresa — mandarla a completar el onboarding en vez de mostrar un panel
 * vacío sin sentido.
 */
export function RequireOrg() {
  const { activeOrg, loading } = useAuth();

  if (loading) return null;
  if (!activeOrg) return <Navigate to="/onboarding" replace />;

  return <Outlet />;
}
