import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { ExternalLink, ListChecks } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { listEvents } from '@/lib/sourcingApi';

const STATUS_VARIANT = {
  DRAFT: 'neutral',
  PUBLISHED: 'success',
  CANCELLED: 'destructive',
  AWARDED: 'brand',
  CLOSED: 'outline',
  VOID: 'destructive',
};
const STATUS_LABELS = {
  DRAFT: 'Borrador',
  PUBLISHED: 'Publicado',
  CANCELLED: 'Cancelado',
  AWARDED: 'Adjudicada',
  CLOSED: 'Cerrado',
  VOID: 'Desierta',
};

// Mismas 5 claves que tabsFor() en SourcingEventLayout.jsx — el link "Ver"
// de cada fila lleva directo a la pestaña de la etapa en la que está hoy,
// no siempre a "Publicar".
const STAGE_LABELS = {
  publicar: 'Publicar',
  match: 'Match',
  evaluacion: 'Evaluación',
  negociacion: 'Negociación',
  adjudicacion: 'Adjudicación',
};
const STAGE_PATH = {
  publicar: (base) => base,
  match: (base) => `${base}/resultados`,
  evaluacion: (base) => `${base}/comite`,
  negociacion: (base) => `${base}/negociacion`,
  adjudicacion: (base) => `${base}/adjudicacion`,
};

function formatDateTime(value) {
  if (!value) return '—';
  return new Intl.DateTimeFormat('es-CL', { dateStyle: 'medium', timeStyle: 'short' }).format(
    new Date(value),
  );
}

export default function SourcingOffersPage() {
  const { activeOrg } = useAuth();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!activeOrg) return;
    setLoading(true);
    listEvents(activeOrg.id)
      .then(setEvents)
      .catch((error) => {
        toast.error(error.response?.data?.detail || 'No se pudieron cargar tus ofertas');
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id]);

  if (!activeOrg) return null;

  return (
    <div className="space-y-6">
      <Helmet>
        <title>Mis ofertas · Directorio de Empresas</title>
      </Helmet>

      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Mis ofertas</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          El consolidado de tus publicaciones y en qué etapa está cada una: match, evaluación,
          negociación o adjudicación.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ListChecks className="size-4 text-primary" />
            Publicaciones ({events.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="h-32 animate-pulse rounded-lg bg-secondary" />
          ) : events.length === 0 ? (
            <p className="px-1 py-8 text-center text-sm text-muted-foreground">
              Aún no tienes publicaciones. Crea una desde Publicar.
            </p>
          ) : (
            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full text-left text-sm">
                <thead className="bg-secondary/50 text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 font-medium">Publicación</th>
                    <th className="px-3 py-2 font-medium">Estado</th>
                    <th className="px-3 py-2 font-medium">Etapa</th>
                    <th className="px-3 py-2 font-medium">Creada el</th>
                    <th className="w-10 px-3 py-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((e) => {
                    const base = `/empresa/sourcing/${e.id}`;
                    const to = (STAGE_PATH[e.stage] || STAGE_PATH.publicar)(base);
                    return (
                      <tr key={e.id} className="border-t">
                        <td className="px-3 py-3 font-medium">
                          {e.name}
                          <p className="text-xs text-muted-foreground">{e.event_code}</p>
                        </td>
                        <td className="px-3 py-3">
                          <Badge variant={STATUS_VARIANT[e.status]}>
                            {STATUS_LABELS[e.status] || e.status}
                          </Badge>
                        </td>
                        <td className="px-3 py-3">
                          <Badge variant="outline">{STAGE_LABELS[e.stage] || e.stage}</Badge>
                        </td>
                        <td className="px-3 py-3 whitespace-nowrap text-muted-foreground">
                          {formatDateTime(e.created_at)}
                        </td>
                        <td className="px-3 py-3">
                          <Link to={to}>
                            <Button variant="outline" size="sm" className="gap-1.5">
                              <ExternalLink className="size-3.5" />
                              Ver
                            </Button>
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
