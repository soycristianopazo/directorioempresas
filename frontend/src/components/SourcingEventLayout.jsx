import { useEffect, useState } from 'react';
import { Outlet, Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { toast } from 'sonner';
import { ArrowLeft } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { getEvent, publishEvent } from '@/lib/sourcingApi';

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

/** Las cuatro etapas que pidió el usuario (Publicar → Match → Evaluación →
 * Adjudicación), con Negociación como paso intermedio reconocido pero no
 * obligatorio. `match` de un tab contra el pathname es por prefijo — así
 * "Evaluación" queda activo tanto en /comite como en /evaluar o
 * /comparador, sus tres sub-vistas. */
function tabsFor(eventId) {
  const base = `/empresa/sourcing/${eventId}`;
  return [
    { key: 'publicar', label: 'Publicar', to: base, match: (p) => p === base },
    {
      key: 'match',
      label: 'Match',
      to: `${base}/resultados`,
      match: (p) => p === `${base}/resultados`,
    },
    {
      key: 'evaluacion',
      label: 'Evaluación',
      to: `${base}/comite`,
      match: (p) =>
        p === `${base}/comite` || p === `${base}/evaluar` || p === `${base}/comparador`,
    },
    {
      key: 'negociacion',
      label: 'Negociación',
      to: `${base}/negociacion`,
      match: (p) => p === `${base}/negociacion`,
    },
    {
      key: 'adjudicacion',
      label: 'Adjudicación',
      to: `${base}/adjudicacion`,
      match: (p) => p === `${base}/adjudicacion`,
    },
  ];
}

const EVALUATION_SUBTABS = [
  { label: 'Comité', suffix: 'comite' },
  { label: 'Evaluar', suffix: 'evaluar' },
  { label: 'Comparador', suffix: 'comparador' },
];

export function SourcingEventLayout() {
  const { eventId } = useParams();
  const { activeOrg } = useAuth();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);

  // Una sola consulta para todo el workspace: layout y las pestañas hijas
  // (vía useOutletContext) comparten este mismo detail en vez de que cada
  // una vuelva a pedir el evento por su cuenta — antes eran hasta 4-6
  // llamadas simultáneas al mismo recurso, algunas se cancelaban entre sí.
  async function load() {
    try {
      setDetail(await getEvent(activeOrg.id, eventId));
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo cargar la publicación');
    }
  }

  useEffect(() => {
    if (!activeOrg) return;
    setLoading(true);
    load().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id, eventId]);

  async function onPublish() {
    try {
      await publishEvent(activeOrg.id, eventId);
      toast.success('Publicación abierta a proveedores');
      // Desde acá el seguimiento pasa a ser el de Match en adelante — el
      // botón Publicar ya no vuelve a aparecer (queda condicionado a DRAFT).
      navigate(`/empresa/sourcing/${eventId}/resultados`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo publicar');
    }
  }

  if (!activeOrg || loading || !detail) {
    return <div className="h-32 animate-pulse rounded-lg bg-secondary" />;
  }

  const { event } = detail;
  const tabs = tabsFor(eventId);
  const base = `/empresa/sourcing/${eventId}`;
  const onEvaluationTab = pathname.startsWith(`${base}/comite`) ||
    pathname.startsWith(`${base}/evaluar`) ||
    pathname.startsWith(`${base}/comparador`);

  return (
    <div className="space-y-6">
      <div>
        <Link
          to="/empresa/ofertas"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" />
          Mis ofertas
        </Link>

        <div className="mt-1 flex items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">{event.name}</h1>
            <p className="mt-0.5 text-sm text-muted-foreground">{event.event_code}</p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Badge variant={STATUS_VARIANT[event.status]}>
              {STATUS_LABELS[event.status] || event.status}
            </Badge>
            {event.status === 'DRAFT' && <Button onClick={onPublish}>Publicar</Button>}
          </div>
        </div>
      </div>

      <nav className="flex gap-1 overflow-x-auto border-b">
        {tabs.map((tab) => {
          const active = tab.match(pathname);
          return (
            <Link
              key={tab.key}
              to={tab.to}
              className={cn(
                'shrink-0 border-b-2 px-3 py-2 text-sm font-medium transition-colors',
                active
                  ? 'border-brand-teal text-brand-teal'
                  : 'border-transparent text-muted-foreground hover:text-foreground',
              )}
            >
              {tab.label}
            </Link>
          );
        })}
      </nav>

      {onEvaluationTab && (
        <div className="-mt-4 flex gap-1.5">
          {EVALUATION_SUBTABS.map((sub) => (
            <Link
              key={sub.suffix}
              to={`${base}/${sub.suffix}`}
              className={cn(
                'rounded-full px-3 py-1 text-xs font-medium',
                pathname === `${base}/${sub.suffix}`
                  ? 'bg-brand-teal text-white'
                  : 'bg-secondary text-muted-foreground hover:text-foreground',
              )}
            >
              {sub.label}
            </Link>
          ))}
        </div>
      )}

      <Outlet
        context={{ event, items: detail.items, criteria: detail.criteria, reloadEvent: load }}
      />
    </div>
  );
}
