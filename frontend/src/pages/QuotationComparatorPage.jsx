import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { useParams } from 'react-router-dom';
import { toast } from 'sonner';
import { Play, Trophy } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { getOrganization } from '@/lib/organizationsApi';
import { getComparator, runComparator } from '@/lib/evaluationsApi';

export default function QuotationComparatorPage() {
  const { eventId } = useParams();
  const { activeOrg } = useAuth();
  const [comparison, setComparison] = useState(null);
  const [orgNames, setOrgNames] = useState({});
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  async function load() {
    try {
      const data = await getComparator(activeOrg.id, eventId);
      setComparison(data);
      if (data?.ranking?.length) {
        const ids = [...new Set(data.ranking.map((r) => r.supplier_organization_id).filter(Boolean))];
        const entries = await Promise.all(
          ids.map(async (id) => {
            try {
              const org = await getOrganization(id);
              return [id, org.trade_name || org.legal_name];
            } catch {
              return [id, `Proveedor ${String(id).slice(0, 8)}`];
            }
          }),
        );
        setOrgNames(Object.fromEntries(entries));
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo cargar el comparador de cotizaciones');
    }
  }

  useEffect(() => {
    if (!activeOrg) return;
    setLoading(true);
    load().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id, eventId]);

  async function handleRun() {
    setRunning(true);
    try {
      await runComparator(activeOrg.id, eventId);
      toast.success('Comparador ejecutado');
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo ejecutar el comparador');
    } finally {
      setRunning(false);
    }
  }

  if (!activeOrg || loading) {
    return <div className="h-32 animate-pulse rounded-lg bg-secondary" />;
  }

  return (
    <div className="space-y-6">
      <Helmet>
        <title>Comparador de ofertas · Directorio de Empresas</title>
      </Helmet>

      <div className="flex items-center justify-end">
        <Button onClick={handleRun} disabled={running} className="gap-1.5">
          <Play className="size-4" />
          {running ? 'Ejecutando…' : 'Ejecutar comparador'}
        </Button>
      </div>

      {!comparison ? (
        <p className="rounded-lg border border-dashed px-4 py-8 text-center text-sm text-muted-foreground">
          Todavía no se ha ejecutado el comparador para este proceso.
        </p>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Ranking ponderado · {new Date(comparison.executed_at).toLocaleString('es-CL')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {comparison.ranking.map((r, i) => (
                <div
                  key={r.quotation_id}
                  className="flex items-center justify-between gap-2 rounded-lg border px-3 py-2"
                >
                  <div className="flex items-center gap-2">
                    {i === 0 && <Trophy className="size-4 text-amber-500" />}
                    <span className="font-medium">
                      {orgNames[r.supplier_organization_id] || 'Proveedor'}
                    </span>
                  </div>
                  <Badge variant={i === 0 ? 'success' : 'outline'}>
                    {r.total_score.toFixed(1)} pts
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
