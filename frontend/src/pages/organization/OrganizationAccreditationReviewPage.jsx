import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { ClipboardCheck } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { EnrollmentReviewPanel } from '@/components/accreditation/EnrollmentReviewPanel';
import { getEnrollmentDetail } from '@/lib/accreditationApi';
import {
  decideEnrollment,
  listOwnReviewQueue,
  reviewFulfillment,
} from '@/lib/organizationAccreditationApi';

/** Cola de revisión de los programas PROPIOS de esta organización
 * (owner_scope=ORGANIZATION) — contraparte de AdminAccreditationPage para
 * el revisor de plataforma. Un programa base de la plataforma (como
 * ACREDITACION_BASE) nunca aparece acá: lo revisa el backoffice. */
export default function OrganizationAccreditationReviewPage() {
  const { activeOrg } = useAuth();
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState(null);

  async function loadQueue() {
    try {
      setQueue(await listOwnReviewQueue(activeOrg.id, 'UNDER_REVIEW'));
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo cargar la cola de revisión propia');
    }
  }

  useEffect(() => {
    if (!activeOrg) return;
    setLoading(true);
    loadQueue().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id]);

  if (!activeOrg) return null;

  return (
    <div className="space-y-8">
      <Helmet>
        <title>Revisión de acreditación propia · Directorio de Empresas</title>
      </Helmet>

      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Revisión de acreditación propia</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Postulaciones en revisión a los programas de acreditación de{' '}
          {activeOrg.trade_name || activeOrg.legal_name}.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ClipboardCheck className="size-4 text-primary" />
            Cola de revisión ({queue.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {loading ? (
            <div className="h-16 animate-pulse rounded-lg bg-secondary" />
          ) : (
            <>
              {queue.map((item) => (
                <div key={item.id} className="rounded-lg border px-3 py-2 text-sm hover:bg-accent/50">
                  <button
                    type="button"
                    className="flex w-full items-center justify-between gap-2 text-left"
                    onClick={() => setSelectedId(selectedId === item.id ? null : item.id)}
                  >
                    <div>
                      <span className="font-medium">{item.organization_name}</span>
                      <span className="ml-2 text-xs text-muted-foreground">{item.program_name}</span>
                    </div>
                    <Badge variant="neutral">{item.completion_pct}%</Badge>
                  </button>
                  {selectedId === item.id && (
                    <EnrollmentReviewPanel
                      item={item}
                      loadDetail={(i) => getEnrollmentDetail(i.organization_id, i.id)}
                      reviewFulfillment={(fulfillmentId, decision) =>
                        reviewFulfillment(activeOrg.id, fulfillmentId, { decision })
                      }
                      decideEnrollment={(decision, reason) =>
                        decideEnrollment(activeOrg.id, item.id, { decision, reason })
                      }
                      onDecided={async () => {
                        setSelectedId(null);
                        await loadQueue();
                      }}
                    />
                  )}
                </div>
              ))}
              {queue.length === 0 && (
                <p className="text-sm text-muted-foreground">No hay postulaciones en revisión.</p>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
