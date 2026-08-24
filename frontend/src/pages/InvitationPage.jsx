import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { useAuth } from '@/context/AuthContext';
import { acceptInvitation } from '@/lib/organizationsApi';
import { Button } from '@/components/ui/button';

export default function InvitationPage() {
  const { token } = useParams();
  const { user, switchOrganization, refresh } = useAuth();
  const navigate = useNavigate();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);

  async function handleAccept() {
    setError(null);
    setPending(true);
    try {
      const organizationId = await acceptInvitation(token);
      await refresh();
      await switchOrganization(organizationId);
      navigate('/dashboard', { replace: true });
    } catch (err) {
      setError(err.response?.data?.detail || 'No se pudo aceptar la invitación');
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center px-6 py-12">
      <Helmet>
        <title>Invitación · Directorio de Empresas</title>
      </Helmet>

      <h1 className="text-2xl font-semibold tracking-tight">Invitación a una organización</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        Estás en sesión como <strong>{user?.email}</strong>. La invitación solo puede aceptarse con
        la dirección a la que fue enviada.
      </p>

      <div className="mt-6 space-y-3">
        <Button onClick={handleAccept} disabled={pending} size="lg" className="w-full">
          {pending ? 'Aceptando…' : 'Aceptar invitación'}
        </Button>
        {error && <p className="text-sm text-destructive">{error}</p>}
      </div>
    </main>
  );
}
