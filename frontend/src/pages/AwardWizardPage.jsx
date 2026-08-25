import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useParams } from 'react-router-dom';
import { toast } from 'sonner';
import { ArrowLeft, Gavel, Send, Upload } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { SelectNative } from '@/components/ui/select-native';
import { Textarea } from '@/components/ui/textarea';
import { getEvent } from '@/lib/sourcingApi';
import { listQuotations } from '@/lib/quotationsApi';
import { listAwards, proposeAward, publishAward } from '@/lib/awardsApi';

const STATUS_VARIANT = {
  DRAFT: 'neutral',
  PENDING_APPROVAL: 'warning',
  APPROVED: 'success',
  REJECTED: 'destructive',
  PUBLISHED: 'brand',
};

const STATUS_LABEL = {
  DRAFT: 'Borrador',
  PENDING_APPROVAL: 'Pendiente de aprobación',
  APPROVED: 'Aprobado',
  REJECTED: 'Rechazado',
  PUBLISHED: 'Publicado',
};

export default function AwardWizardPage() {
  const { eventId } = useParams();
  const { activeOrg } = useAuth();
  const [event, setEvent] = useState(null);
  const [items, setItems] = useState([]);
  const [quotations, setQuotations] = useState([]);
  const [awards, setAwards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedQuotationId, setSelectedQuotationId] = useState('');
  const [justification, setJustification] = useState('');
  const [lines, setLines] = useState({});

  async function load() {
    const [detail, qs, aw] = await Promise.all([
      getEvent(activeOrg.id, eventId),
      listQuotations(activeOrg.id, eventId),
      listAwards(activeOrg.id, eventId),
    ]);
    setEvent(detail.event);
    setItems(detail.items);
    setQuotations(qs);
    setAwards(aw);
  }

  useEffect(() => {
    if (!activeOrg) return;
    setLoading(true);
    load().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id, eventId]);

  function updateLine(itemId, value) {
    setLines((prev) => ({ ...prev, [itemId]: value }));
  }

  async function handlePropose(e) {
    e.preventDefault();
    const quotation = quotations.find((q) => q.id === selectedQuotationId);
    if (!quotation || !quotation.current_revision_id) {
      toast.error('Selecciona una cotización con una revisión enviada');
      return;
    }
    const proposedItems = items
      .map((item) => ({
        sourcingEventItemId: item.id,
        quantity: item.quantity,
        unitPrice: Number(lines[item.id]) || 0,
      }))
      .filter((i) => i.unitPrice > 0);
    if (proposedItems.length === 0) {
      toast.error('Ingresa el precio unitario de al menos una línea');
      return;
    }
    try {
      await proposeAward(activeOrg.id, eventId, {
        awardedOrganizationId: quotation.supplier_organization_id,
        quotationRevisionId: quotation.current_revision_id,
        justification: justification || null,
        items: proposedItems,
      });
      toast.success('Adjudicación propuesta');
      setJustification('');
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo proponer la adjudicación');
    }
  }

  async function handlePublish(awardId) {
    try {
      await publishAward(activeOrg.id, eventId, awardId);
      toast.success('Adjudicación publicada — proceso cerrado');
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo publicar');
    }
  }

  if (!activeOrg || loading || !event) {
    return <div className="h-32 animate-pulse rounded-lg bg-secondary" />;
  }

  return (
    <div className="space-y-6">
      <Helmet>
        <title>Adjudicación · Directorio de Empresas</title>
      </Helmet>

      <div>
        <Link
          to={`/empresa/sourcing/${eventId}`}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" />
          Volver al proceso
        </Link>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">Adjudicación</h1>
        <p className="mt-1 text-sm text-muted-foreground">{event.name}</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Gavel className="size-4 text-primary" />
            Proponer adjudicación
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handlePropose} className="space-y-4">
            <div className="space-y-1.5">
              <Label>Proveedor ganador</Label>
              <SelectNative
                value={selectedQuotationId}
                onChange={(e) => setSelectedQuotationId(e.target.value)}
                className="max-w-md"
              >
                <option value="">Elegir cotización…</option>
                {quotations.map((q) => (
                  <option key={q.id} value={q.id}>
                    Proveedor {String(q.supplier_organization_id).slice(0, 8)}
                    {q.total_amount != null ? ` — ${q.total_amount} ${q.currency_code}` : ''}
                  </option>
                ))}
              </SelectNative>
            </div>

            <div className="space-y-2">
              <h3 className="text-sm font-medium">Precios adjudicados por línea</h3>
              {items.map((item) => (
                <div key={item.id} className="flex items-center gap-2 text-sm">
                  <span className="min-w-[16rem]">{item.description}</span>
                  <Input
                    type="number"
                    min="0"
                    step="any"
                    className="w-32"
                    value={lines[item.id] ?? ''}
                    onChange={(e) => updateLine(item.id, e.target.value)}
                  />
                </div>
              ))}
            </div>

            <div className="space-y-1.5">
              <Label>Justificación (opcional)</Label>
              <Textarea value={justification} onChange={(e) => setJustification(e.target.value)} />
            </div>

            <Button type="submit" className="gap-1.5">
              <Send className="size-4" />
              Proponer adjudicación
            </Button>
          </form>
        </CardContent>
      </Card>

      <div className="space-y-3">
        {awards.length === 0 ? (
          <p className="rounded-lg border border-dashed px-4 py-8 text-center text-sm text-muted-foreground">
            Sin propuestas de adjudicación todavía.
          </p>
        ) : (
          awards.map((a) => (
            <Card key={a.id}>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-base">
                  Proveedor {String(a.awarded_organization_id).slice(0, 8)} — {a.amount} {a.currency_code}
                </CardTitle>
                <div className="flex items-center gap-2">
                  <Badge variant={STATUS_VARIANT[a.status] || 'outline'}>
                    {STATUS_LABEL[a.status] || a.status}
                  </Badge>
                  {a.status === 'APPROVED' && (
                    <Button size="sm" className="gap-1.5" onClick={() => handlePublish(a.id)}>
                      <Upload className="size-3.5" />
                      Publicar y cerrar
                    </Button>
                  )}
                </div>
              </CardHeader>
              {a.justification && (
                <CardContent>
                  <p className="text-sm text-muted-foreground">{a.justification}</p>
                </CardContent>
              )}
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
