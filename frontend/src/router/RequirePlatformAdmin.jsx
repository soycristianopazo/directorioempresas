import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';

/**
 * Exige que el usuario autenticado tenga el rol de plataforma. Hermano de
 * RequireOrg, no anidado dentro: un platform admin puro (cuenta de
 * backoffice, ver seed.py) puede no pertenecer a ninguna organización.
 *
 * La autoridad real es RLS + el chequeo del servicio en el backend
 * (app.has_platform_permission) — esto solo evita mostrar un enlace o una
 * pantalla que de todos modos rechazaría cualquier acción.
 */
export function RequirePlatformAdmin() {
  const { isPlatformAdmin, loading } = useAuth();

  if (loading) return null;
  if (!isPlatformAdmin) return <Navigate to="/dashboard" replace />;

  return <Outlet />;
}
