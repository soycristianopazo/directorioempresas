import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { FileSearch, Plus } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { createEvent, listEvents } from '@/lib/sourcingApi';

const STATUS_VARIANT = {
  PUBLISHED: 'bg-emerald-600 text-white hover:bg-emerald-600',
  CANCELLED: 'bg-destructive text-destructive-foreground hover:bg-destructive',
};
const STATUS_LABELS = { DRAFT: 'Borrador', PUBLISHED: 'Publicado', CANCELLED: 'Cancelado' };

export default function SourcingEventsPage() {
  const { activeOrg } = useAuth();
  const navigate = useNavigate();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  async function loadAll() {
    setEvents(await listEvents(activeOrg.id));
  }

  useEffect(() => {
    if (!activeOrg) return;
    setLoading(true);
    loadAll().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id]);

  async function onCreateBlank() {
    try {
      const eventId = await createEvent(activeOrg.id, { name: 'Nuevo proceso de sourcing' });
      navigate(`/empresa/sourcing/${eventId}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo crear el proceso');
    }
  }

  if (!activeOrg) return null;

  return (
    <div className="space-y-8">
      <Helmet>
        <title>Procesos de sourcing · Directorio de Empresas</title>
      </Helmet>

      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Procesos de sourcing</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Define líneas y criterios, y encuentra proveedores que califican.
          </p>
        </div>
        <Button onClick={onCreateBlank}>
          <Plus className="size-4" />
          Nuevo proceso
        </Button>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileSearch className="size-4 text-primary" />
            Mis procesos ({events.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {loading ? (
            <div className="h-16 animate-pulse rounded-lg bg-secondary" />
          ) : (
            <>
              {events.map((e) => (
                <Link
                  key={e.id}
                  to={`/empresa/sourcing/${e.id}`}
                  className="flex items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm hover:bg-accent/50"
                >
                  <div>
                    <span className="font-medium">{e.name}</span>
                    <span className="ml-2 text-xs text-muted-foreground">{e.event_code}</span>
                  </div>
                  <Badge className={STATUS_VARIANT[e.status]}>
                    {STATUS_LABELS[e.status] || e.status}
                  </Badge>
                </Link>
              ))}
              {events.length === 0 && (
                <p className="text-sm text-muted-foreground">Aún no tienes procesos de sourcing.</p>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
