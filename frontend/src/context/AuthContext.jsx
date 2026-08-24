import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import api, { getAccessToken, setAccessToken } from '@/lib/api';

/**
 * Sesión del usuario. Consume el backend FastAPI portado en backend/app.
 *
 * Al montar, intenta refrescar la sesión desde la cookie httpOnly antes de
 * decidir "no hay sesión": si el usuario cerró la pestaña con un refresh
 * token todavía vigente, no debe tener que volver a loguearse.
 */

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [activeOrgId, setActiveOrgId] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchMe = useCallback(async () => {
    const { data } = await api.get('/auth/me');
    setUser(data.user);
    setActiveOrgId((current) => current ?? data.user.last_org_id ?? null);
    return data.user;
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      try {
        if (!getAccessToken()) {
          // Sin access token en memoria: intenta canjear la cookie de refresh.
          const { data } = await api.post('/auth/refresh');
          setAccessToken(data.access_token);
        }
        const me = await fetchMe();
        if (!cancelled) setUser(me);
      } catch {
        if (!cancelled) {
          setAccessToken(null);
          setUser(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    bootstrap();

    function onSessionExpired() {
      setUser(null);
      setActiveOrgId(null);
    }
    window.addEventListener('auth:session-expired', onSessionExpired);

    return () => {
      cancelled = true;
      window.removeEventListener('auth:session-expired', onSessionExpired);
    };
  }, [fetchMe]);

  const login = useCallback(
    async (email, password) => {
      const { data } = await api.post('/auth/login', { email, password });
      setAccessToken(data.access_token);
      const me = await fetchMe();
      return me;
    },
    [fetchMe],
  );

  const register = useCallback(async ({ firstName, lastName, email, password }) => {
    const { data } = await api.post('/auth/register', {
      first_name: firstName,
      last_name: lastName,
      email,
      password,
    });
    setAccessToken(data.access_token);
    setUser(data.user);
    return data.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout');
    } finally {
      setAccessToken(null);
      setUser(null);
      setActiveOrgId(null);
    }
  }, []);

  const switchOrganization = useCallback(async (organizationId) => {
    await api.post('/organizations/switch', { organization_id: organizationId });
    setActiveOrgId(organizationId);
  }, []);

  const activeOrg = useMemo(
    () => user?.memberships?.find((m) => m.id === activeOrgId) ?? user?.memberships?.[0] ?? null,
    [user, activeOrgId],
  );

  const value = useMemo(
    () => ({
      user,
      loading,
      isAuthenticated: Boolean(user),
      memberships: user?.memberships ?? [],
      activeOrg,
      login,
      register,
      logout,
      switchOrganization,
      refresh: fetchMe,
    }),
    [user, loading, activeOrg, login, register, logout, switchOrganization, fetchMe],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth() debe usarse dentro de <AuthProvider>');
  }
  return ctx;
}
