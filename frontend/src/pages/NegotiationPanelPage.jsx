import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { useOutletContext, useParams } from 'react-router-dom';
import { toast } from 'sonner';
import { Plus, X } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { SelectNative } from '@/components/ui/select-native';
import { Textarea } from '@/components/ui/textarea';
import { ConversationPanel } from '@/components/ConversationPanel';
import { listQuotations } from '@/lib/quotationsApi';
import { listRounds, openRound, closeRound } from '@/lib/negotiationsApi';

export default function NegotiationPanelPage() {
  const { eventId } = useParams();
  const { activeOrg } = useAuth();
  const { event } = useOutletContext();
  const [quotations, setQuotations] = useState([]);
  const [rounds, setRounds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showOpenForm, setShowOpenForm] = useState(false);
  const [form, setForm] = useState({
    roundType: 'BAFO',
    deadline: '',
    targetReductionPct: '',
    instructions: '',
    participants: [],
  });

  async function load() {
    try {
      const [qs, rs] = await Promise.all([
        listQuotations(activeOrg.id, eventId),
        listRounds(activeOrg.id, eventId),
      ]);
      setQuotations(qs);
      setRounds(rs);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo cargar el panel de negociación');
    }
  }

  useEffect(() => {
    if (!activeOrg) return;
    setLoading(true);
    load().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id, eventId]);

  function toggleParticipant(orgId) {
    setForm((f) => ({
      ...f,
      participants: f.participants.includes(orgId)
        ? f.participants.filter((id) => id !== orgId)
        : [...f.participants, orgId],
    }));
  }

  async function handleOpenRound(e) {
    e.preventDefault();
    if (form.participants.length === 0) {
      toast.error('Selecciona al menos un proveedor');
      return;
    }
    try {
      await openRound(activeOrg.id, eventId, {
        roundType: form.roundType,
        participantSupplierOrganizationIds: form.participants,
        deadline: form.deadline ? new Date(form.deadline).toISOString() : null,
        targetReductionPct: form.targetReductionPct ? Number(form.targetReductionPct) : null,
        instructions: form.instructions || null,
      });
      toast.success('Ronda abierta');
      setShowOpenForm(false);
      setForm({ roundType: 'BAFO', deadline: '', targetReductionPct: '', instructions: '', participants: [] });
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo abrir la ronda');
    }
  }

  async function handleClose(roundId) {
    try {
      await closeRound(activeOrg.id, eventId, roundId);
      toast.success('Ronda cerrada');
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo cerrar la ronda');
    }
  }

  if (!activeOrg || loading || !event) {
    return <div className="h-32 animate-pulse rounded-lg bg-secondary" />;
  }

  return (
    <div className="space-y-6">
      <Helmet>
        <title>Negociación · Directorio de Empresas</title>
      </Helmet>

      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Para aclaraciones (sin cambio de monto) usa la mensajería del proceso, más abajo.
        </p>
        <Button className="gap-1.5" onClick={() => setShowOpenForm((v) => !v)}>
          {showOpenForm ? <X className="size-4" /> : <Plus className="size-4" />}
          {showOpenForm ? 'Cancelar' : 'Abrir ronda'}
        </Button>
      </div>

      {showOpenForm && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Nueva ronda</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleOpenRound} className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="space-y-1.5">
                  <Label>Tipo</Label>
                  <SelectNative
                    value={form.roundType}
                    onChange={(e) => setForm((f) => ({ ...f, roundType: e.target.value }))}
                  >
                    <option value="COUNTER">Contraoferta</option>
                    <option value="BAFO">Mejor oferta final (BAFO)</option>
                  </SelectNative>
                </div>
                <div className="space-y-1.5">
                  <Label>Plazo (opcional)</Label>
                  <Input
                    type="datetime-local"
                    value={form.deadline}
                    onChange={(e) => setForm((f) => ({ ...f, deadline: e.target.value }))}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label>Reducción objetivo % (opcional)</Label>
                  <Input
                    type="number"
                    min="0"
                    value={form.targetReductionPct}
                    onChange={(e) => setForm((f) => ({ ...f, targetReductionPct: e.target.value }))}
                  />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label>Instrucciones (opcional)</Label>
                <Textarea
                  value={form.instructions}
                  onChange={(e) => setForm((f) => ({ ...f, instructions: e.target.value }))}
                />
              </div>
              <div className="space-y-1.5">
                <Label>Proveedores participantes</Label>
                <div className="flex flex-wrap gap-2">
                  {quotations.map((q) => (
                    <Button
                      key={q.id}
                      type="button"
                      variant={form.participants.includes(q.supplier_organization_id) ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => toggleParticipant(q.supplier_organization_id)}
                    >
                      Proveedor {String(q.supplier_organization_id).slice(0, 8)}
                    </Button>
                  ))}
                  {quotations.length === 0 && (
                    <p className="text-sm text-muted-foreground">Sin cotizaciones recibidas todavía.</p>
                  )}
                </div>
              </div>
              <Button type="submit">Abrir ronda</Button>
            </form>
          </CardContent>
        </Card>
      )}

      <div className="space-y-3">
        {rounds.length === 0 ? (
          <p className="rounded-lg border border-dashed px-4 py-8 text-center text-sm text-muted-foreground">
            Sin rondas de negociación todavía.
          </p>
        ) : (
          rounds.map((r) => (
            <Card key={r.id}>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-base">
                  {r.round_type === 'BAFO' ? 'Mejor oferta final' : 'Contraoferta'}
                </CardTitle>
                <div className="flex items-center gap-2">
                  <Badge variant={r.closed_at ? 'outline' : 'success'}>
                    {r.closed_at ? 'Cerrada' : 'Abierta'}
                  </Badge>
                  {!r.closed_at && (
                    <Button variant="outline" size="sm" onClick={() => handleClose(r.id)}>
                      Cerrar ronda
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-1 text-sm text-muted-foreground">
                {r.instructions && <p>{r.instructions}</p>}
                {r.deadline && <p>Plazo: {new Date(r.deadline).toLocaleString('es-CL')}</p>}
                {r.target_reduction_pct != null && <p>Reducción objetivo: {r.target_reduction_pct}%</p>}
              </CardContent>
            </Card>
          ))
        )}
      </div>

      <ConversationPanel
        organizationId={activeOrg.id}
        contextType="SOURCING_EVENT"
        contextId={eventId}
        participantOrganizationIds={quotations.map((q) => q.supplier_organization_id)}
      />
    </div>
  );
}
