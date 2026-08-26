import { useEffect, useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { useParams } from 'react-router-dom';
import { toast } from 'sonner';
import { Calculator, FileText, Send } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { ConversationPanel } from '@/components/ConversationPanel';
import { getEvent } from '@/lib/sourcingApi';
import { listMyRevisions, submitRevision } from '@/lib/quotationsApi';
import { listMyRound, submitCounter } from '@/lib/negotiationsApi';

function formatDateTime(value) {
  if (!value) return '—';
  return new Intl.DateTimeFormat('es-CL', { dateStyle: 'medium', timeStyle: 'short' }).format(
    new Date(value),
  );
}

function emptyLineFor(item) {
  return {
    quantity: String(item.quantity ?? ''),
    unitPrice: '',
    discountPct: '',
    leadTimeDays: '',
  };
}

export default function SupplierQuotationPage() {
  const { eventId } = useParams();
  const { activeOrg } = useAuth();
  const [detail, setDetail] = useState(null);
  const [revisions, setRevisions] = useState([]);
  const [activeRound, setActiveRound] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const [lines, setLines] = useState({});
  const [form, setForm] = useState({
    currencyCode: 'CLP',
    validUntil: '',
    subtotal: '',
    taxAmount: '',
    totalAmount: '',
    paymentTerms: '',
    deliveryDays: '',
    warrantyTerms: '',
    exclusions: '',
    notes: '',
  });

  async function loadAll() {
    try {
      const d = await getEvent(activeOrg.id, eventId);
      setDetail(d);
      setLines((prev) => {
        if (Object.keys(prev).length > 0) return prev;
        return Object.fromEntries(d.items.map((item) => [item.id, emptyLineFor(item)]));
      });
      setRevisions(await listMyRevisions(activeOrg.id, eventId));
      const rounds = await listMyRound(activeOrg.id, eventId);
      setActiveRound(rounds.find((r) => !r.closed_at && !r.responded_at) || null);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo cargar la cotización');
    }
  }

  useEffect(() => {
    if (!activeOrg) return;
    setLoading(true);
    loadAll().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id, eventId]);

  function updateLine(itemId, field, value) {
    setLines((prev) => ({ ...prev, [itemId]: { ...prev[itemId], [field]: value } }));
  }

  function updateForm(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  const preview = useMemo(() => {
    if (!detail) return 0;
    return detail.items.reduce((sum, item) => {
      const line = lines[item.id];
      if (!line) return sum;
      const qty = Number(line.quantity) || 0;
      const price = Number(line.unitPrice) || 0;
      const discount = Number(line.discountPct) || 0;
      return sum + qty * price * (1 - discount / 100);
    }, 0);
  }, [detail, lines]);

  async function onSubmit(e) {
    e.preventDefault();
    if (!form.currencyCode.trim()) {
      toast.error('Ingresa una moneda');
      return;
    }
    if (!form.totalAmount) {
      toast.error('Ingresa el monto total de la oferta');
      return;
    }
    const items = detail.items.map((item) => {
      const line = lines[item.id] || {};
      return {
        sourcingEventItemId: item.id,
        quantity: Number(line.quantity) || item.quantity,
        unitCode: item.unit_code || null,
        unitPrice: Number(line.unitPrice) || 0,
        discountPct: line.discountPct ? Number(line.discountPct) : null,
        leadTimeDays: line.leadTimeDays ? Number(line.leadTimeDays) : null,
      };
    });

    const payload = {
      currencyCode: form.currencyCode.trim(),
      validUntil: form.validUntil || null,
      subtotal: form.subtotal ? Number(form.subtotal) : null,
      taxAmount: form.taxAmount ? Number(form.taxAmount) : null,
      totalAmount: Number(form.totalAmount),
      paymentTerms: form.paymentTerms || null,
      deliveryDays: form.deliveryDays ? Number(form.deliveryDays) : null,
      warrantyTerms: form.warrantyTerms || null,
      exclusions: form.exclusions || null,
      notes: form.notes || null,
      items,
    };

    setSubmitting(true);
    try {
      if (activeRound) {
        await submitCounter(activeOrg.id, eventId, activeRound.id, payload);
        toast.success('Contraoferta enviada');
      } else {
        await submitRevision(activeOrg.id, eventId, payload);
        toast.success('Cotización enviada');
      }
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo enviar la oferta');
    } finally {
      setSubmitting(false);
    }
  }

  if (!activeOrg || loading || !detail) {
    return <div className="h-32 animate-pulse rounded-lg bg-secondary" />;
  }

  const { event, items } = detail;

  return (
    <div className="space-y-8">
      <Helmet>
        <title>Mi cotización · {event.name} · Directorio de Empresas</title>
      </Helmet>

      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Mi cotización</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {event.name} · {event.event_code}
        </p>
      </header>

      {activeRound && (
        <Card className="border-amber-300 bg-amber-50 dark:bg-amber-950/20">
          <CardContent className="pt-6 text-sm">
            <p className="font-medium">
              {activeRound.round_type === 'BAFO' ? 'Mejor oferta final solicitada' : 'Contraoferta solicitada'}
            </p>
            {activeRound.instructions && <p className="mt-1">{activeRound.instructions}</p>}
            {activeRound.target_reduction_pct != null && (
              <p className="mt-1">Reducción objetivo: {activeRound.target_reduction_pct}%</p>
            )}
            {activeRound.deadline && (
              <p className="mt-1">Responder antes de: {formatDateTime(activeRound.deadline)}</p>
            )}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="size-4 text-primary" />
            {activeRound ? 'Responder a la ronda de negociación' : 'Nueva revisión'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-6">
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="space-y-1.5">
                <Label htmlFor="currency">Moneda</Label>
                <Input
                  id="currency"
                  value={form.currencyCode}
                  onChange={(e) => updateForm('currencyCode', e.target.value)}
                  placeholder="CLP"
                />
                <p className="text-xs text-muted-foreground">
                  También se aceptan códigos como UF o UTM.
                </p>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="validUntil">Válida hasta (opcional)</Label>
                <Input
                  id="validUntil"
                  type="date"
                  value={form.validUntil}
                  onChange={(e) => updateForm('validUntil', e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="deliveryDays">Plazo de entrega en días (opcional)</Label>
                <Input
                  id="deliveryDays"
                  type="number"
                  min={0}
                  value={form.deliveryDays}
                  onChange={(e) => updateForm('deliveryDays', e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-2">
              <h3 className="text-sm font-medium">Líneas a cotizar</h3>
              <div className="overflow-x-auto rounded-lg border">
                <table className="w-full min-w-[720px] text-sm">
                  <thead className="border-b bg-secondary/50 text-xs uppercase text-muted-foreground">
                    <tr>
                      <th className="px-3 py-2 text-left">Descripción</th>
                      <th className="px-3 py-2 text-left">Cantidad</th>
                      <th className="px-3 py-2 text-left">Precio unitario</th>
                      <th className="px-3 py-2 text-left">Descuento %</th>
                      <th className="px-3 py-2 text-left">Plazo (días)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((item) => (
                      <tr key={item.id} className="border-b last:border-b-0">
                        <td className="px-3 py-2">
                          {item.description}
                          {item.unit_code && (
                            <span className="ml-1 text-xs text-muted-foreground">
                              ({item.unit_code})
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-2">
                          <Input
                            type="number"
                            min={0}
                            step="any"
                            className="w-24"
                            value={lines[item.id]?.quantity ?? ''}
                            onChange={(e) => updateLine(item.id, 'quantity', e.target.value)}
                          />
                        </td>
                        <td className="px-3 py-2">
                          <Input
                            type="number"
                            min={0}
                            step="any"
                            className="w-32"
                            value={lines[item.id]?.unitPrice ?? ''}
                            onChange={(e) => updateLine(item.id, 'unitPrice', e.target.value)}
                          />
                        </td>
                        <td className="px-3 py-2">
                          <Input
                            type="number"
                            min={0}
                            max={100}
                            step="any"
                            className="w-24"
                            value={lines[item.id]?.discountPct ?? ''}
                            onChange={(e) => updateLine(item.id, 'discountPct', e.target.value)}
                          />
                        </td>
                        <td className="px-3 py-2">
                          <Input
                            type="number"
                            min={0}
                            className="w-24"
                            value={lines[item.id]?.leadTimeDays ?? ''}
                            onChange={(e) => updateLine(item.id, 'leadTimeDays', e.target.value)}
                          />
                        </td>
                      </tr>
                    ))}
                    {items.length === 0 && (
                      <tr>
                        <td colSpan={5} className="px-3 py-4 text-center text-muted-foreground">
                          Este proceso no tiene líneas definidas.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
                <Calculator className="size-3.5" />
                Total estimado de las líneas: {preview.toLocaleString('es-CL')} {form.currencyCode}
              </p>
            </div>

            <div className="grid gap-3 border-t pt-4 sm:grid-cols-3">
              <div className="space-y-1.5">
                <Label htmlFor="subtotal">Subtotal (opcional)</Label>
                <Input
                  id="subtotal"
                  type="number"
                  step="any"
                  value={form.subtotal}
                  onChange={(e) => updateForm('subtotal', e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="taxAmount">Impuestos (opcional)</Label>
                <Input
                  id="taxAmount"
                  type="number"
                  step="any"
                  value={form.taxAmount}
                  onChange={(e) => updateForm('taxAmount', e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="totalAmount">Monto total de la oferta</Label>
                <div className="flex gap-1.5">
                  <Input
                    id="totalAmount"
                    type="number"
                    step="any"
                    value={form.totalAmount}
                    onChange={(e) => updateForm('totalAmount', e.target.value)}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => updateForm('totalAmount', String(preview))}
                  >
                    Usar estimado
                  </Button>
                </div>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="paymentTerms">Condiciones de pago (opcional)</Label>
                <Input
                  id="paymentTerms"
                  value={form.paymentTerms}
                  onChange={(e) => updateForm('paymentTerms', e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="warrantyTerms">Garantía (opcional)</Label>
                <Input
                  id="warrantyTerms"
                  value={form.warrantyTerms}
                  onChange={(e) => updateForm('warrantyTerms', e.target.value)}
                />
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="exclusions">Exclusiones (opcional)</Label>
                <Textarea
                  id="exclusions"
                  value={form.exclusions}
                  onChange={(e) => updateForm('exclusions', e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="notes">Notas (opcional)</Label>
                <Textarea
                  id="notes"
                  value={form.notes}
                  onChange={(e) => updateForm('notes', e.target.value)}
                />
              </div>
            </div>

            <Button type="submit" disabled={submitting} className="gap-1.5">
              <Send className="size-4" />
              {submitting ? 'Enviando…' : activeRound ? 'Enviar contraoferta' : 'Enviar cotización'}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Historial de envíos ({revisions.length})</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {revisions.map((r) => (
            <div
              key={r.id}
              className="flex items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm"
            >
              <div>
                <Badge variant="brand" className="mr-2">
                  Ronda {r.round_number}
                </Badge>
                {formatDateTime(r.submitted_at)}
              </div>
              <span className="font-medium">
                {r.total_amount?.toLocaleString('es-CL')} {r.currency_code}
              </span>
            </div>
          ))}
          {revisions.length === 0 && (
            <p className="text-sm text-muted-foreground">Aún no has enviado ninguna cotización.</p>
          )}
        </CardContent>
      </Card>

      <ConversationPanel
        organizationId={activeOrg.id}
        contextType="SOURCING_EVENT"
        contextId={eventId}
        participantOrganizationIds={[event.organization_id]}
      />
    </div>
  );
}
