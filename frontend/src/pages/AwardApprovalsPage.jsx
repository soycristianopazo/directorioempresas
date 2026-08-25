import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { toast } from 'sonner';
import { Check, ClipboardCheck, X } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { listMyPendingApprovals, decideApproval } from '@/lib/awardsApi';

export default function AwardApprovalsPage() {
  const { activeOrg } = useAuth();
  const [approvals, setApprovals] = useState([]);
  const [comments, setComments] = useState({});
  const [loading, setLoading] = useState(true);

  async function load() {
    const rows = await listMyPendingApprovals(activeOrg.id);
    setApprovals(rows.filter((a) => a.status === 'PENDING'));
  }

  useEffect(() => {
    if (!activeOrg) return;
    setLoading(true);
    load().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id]);

  async function handleDecide(approvalId, decision) {
    try {
      await decideApproval(activeOrg.id, approvalId, decision, comments[approvalId]);
      toast.success(decision === 'APPROVED' ? 'Aprobado' : 'Rechazado');
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo registrar la decisión');
    }
  }

  if (!activeOrg) return null;

  return (
    <div className="space-y-6">
      <Helmet>
        <title>Aprobaciones pendientes · Directorio de Empresas</title>
      </Helmet>

      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Aprobaciones pendientes</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Adjudicaciones que necesitan tu aprobación según tu límite delegado.
        </p>
      </header>

      {loading ? (
        <div className="h-24 animate-pulse rounded-lg bg-secondary" />
      ) : approvals.length === 0 ? (
        <p className="rounded-lg border border-dashed px-4 py-8 text-center text-sm text-muted-foreground">
          No tienes aprobaciones pendientes.
        </p>
      ) : (
        <div className="space-y-3">
          {approvals.map((a) => (
            <Card key={a.id}>
              <CardHeader className="flex flex-row items-center gap-2">
                <ClipboardCheck className="size-4 text-primary" />
                <CardTitle className="text-base">
                  Paso {a.step_order} — {a.required_role_code}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Textarea
                  placeholder="Comentario (opcional)"
                  value={comments[a.id] || ''}
                  onChange={(e) => setComments((prev) => ({ ...prev, [a.id]: e.target.value }))}
                />
                <div className="flex gap-2">
                  <Button className="gap-1.5" onClick={() => handleDecide(a.id, 'APPROVED')}>
                    <Check className="size-4" />
                    Aprobar
                  </Button>
                  <Button
                    variant="outline"
                    className="gap-1.5"
                    onClick={() => handleDecide(a.id, 'REJECTED')}
                  >
                    <X className="size-4" />
                    Rechazar
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
