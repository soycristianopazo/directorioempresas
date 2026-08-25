import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useParams } from 'react-router-dom';
import { toast } from 'sonner';
import { ArrowLeft, CheckCircle2, Lock } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { getOrganization } from '@/lib/organizationsApi';
import { getMyEvaluationView, submitScore, submitEvaluation } from '@/lib/evaluationsApi';

function groupBy(rows, key) {
  const out = {};
  for (const row of rows) {
    const k = String(row[key]);
    (out[k] ||= []).push(row);
  }
  return out;
}

export default function EvaluationFormPage() {
  const { eventId } = useParams();
  const { activeOrg } = useAuth();
  const [view, setView] = useState(null);
  const [orgNames, setOrgNames] = useState({});
  const [loading, setLoading] = useState(true);

  async function load() {
    const data = await getMyEvaluationView(activeOrg.id, eventId);
    setView(data);
    const supplierIds = [...new Set(data.items.map((i) => i.supplier_organization_id))];
    const entries = await Promise.all(
      supplierIds.map(async (id) => {
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

  useEffect(() => {
    if (!activeOrg) return;
    setLoading(true);
    load()
      .catch((error) => toast.error(error.response?.data?.detail || 'No se pudo cargar'))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id, eventId]);

  if (!activeOrg || loading || !view) {
    return <div className="h-32 animate-pulse rounded-lg bg-secondary" />;
  }

  const itemsByQuotation = groupBy(view.items, 'quotation_id');
  const responsesByQuotation = groupBy(view.responses, 'quotation_id');
  const documentsByQuotation = groupBy(view.documents, 'quotation_id');
  const revisionsByQuotation = groupBy(view.revisions, 'quotation_id');

  return (
    <div className="space-y-6">
      <Helmet>
        <title>Evaluar ofertas · Directorio de Empresas</title>
      </Helmet>

      <div>
        <Link
          to={`/empresa/sourcing/${eventId}`}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" />
          Volver al proceso
        </Link>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">Evaluar ofertas</h1>
        <p className="mt-1 flex items-center gap-1.5 text-sm text-muted-foreground">
          {view.can_view_commercial ? (
            'Tienes acceso a montos (tras la apertura de sobres).'
          ) : (
            <>
              <Lock className="size-3.5" />
              Vista técnica — sin acceso a montos.
            </>
          )}
        </p>
      </div>

      {Object.keys(itemsByQuotation).length === 0 ? (
        <p className="rounded-lg border border-dashed px-4 py-8 text-center text-sm text-muted-foreground">
          Todavía no hay ofertas para evaluar.
        </p>
      ) : (
        Object.entries(itemsByQuotation).map(([quotationId, items]) => (
          <QuotationCard
            key={quotationId}
            organizationId={activeOrg.id}
            eventId={eventId}
            quotationId={quotationId}
            supplierName={orgNames[items[0]?.supplier_organization_id] || 'Proveedor'}
            items={items}
            responses={responsesByQuotation[quotationId] || []}
            documents={documentsByQuotation[quotationId] || []}
            revisions={revisionsByQuotation[quotationId] || []}
            criteria={view.criteria}
            canViewCommercial={view.can_view_commercial}
            evaluation={view.evaluations[quotationId]}
            onChanged={load}
          />
        ))
      )}
    </div>
  );
}

function QuotationCard({
  organizationId,
  eventId,
  quotationId,
  supplierName,
  items,
  responses,
  documents,
  revisions,
  criteria,
  canViewCommercial,
  evaluation,
  onChanged,
}) {
  const [scores, setScores] = useState(() => {
    const initial = {};
    for (const s of evaluation?.scores || []) {
      initial[s.evaluation_criterion_id] = { score: s.score, comment: s.comment || '' };
    }
    return initial;
  });
  const [comment, setComment] = useState(evaluation?.overall_comment || '');
  const submitted = evaluation?.status === 'SUBMITTED';
  const latestRevision = revisions[revisions.length - 1];

  function updateScore(criterionId, field, value) {
    setScores((prev) => ({
      ...prev,
      [criterionId]: { ...prev[criterionId], [field]: value },
    }));
  }

  async function handleSaveScore(criterionId) {
    const row = scores[criterionId];
    if (!row || row.score === undefined || row.score === '') return;
    try {
      await submitScore(organizationId, eventId, {
        quotationId,
        evaluationCriterionId: criterionId,
        score: Number(row.score),
        comment: row.comment,
      });
      toast.success('Puntaje guardado');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo guardar el puntaje');
    }
  }

  async function handleSubmit() {
    try {
      await submitEvaluation(organizationId, eventId, quotationId, comment);
      toast.success('Evaluación enviada');
      await onChanged();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo enviar la evaluación');
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base">{supplierName}</CardTitle>
        {submitted ? (
          <Badge variant="success" className="gap-1">
            <CheckCircle2 className="size-3.5" />
            Enviada
          </Badge>
        ) : (
          <Badge variant="outline">Borrador</Badge>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <h4 className="text-sm font-medium">Líneas ofertadas</h4>
          <ul className="mt-1 space-y-1 text-sm text-muted-foreground">
            {items.map((i) => (
              <li key={i.item_id}>
                {i.quantity} {i.unit_code || ''} — {i.brand || 'Sin marca'} {i.model || ''}
                {i.lead_time_days != null && ` · ${i.lead_time_days} días de entrega`}
              </li>
            ))}
          </ul>
        </div>

        {responses.length > 0 && (
          <div>
            <h4 className="text-sm font-medium">Respuestas a criterios de matching</h4>
            <ul className="mt-1 space-y-1 text-sm text-muted-foreground">
              {responses.map((r) => (
                <li key={r.response_id}>
                  {r.complies === true ? '✓' : r.complies === false ? '✗' : '—'}{' '}
                  {r.value_text || ''} {r.notes || ''}
                </li>
              ))}
            </ul>
          </div>
        )}

        {documents.length > 0 && (
          <div>
            <h4 className="text-sm font-medium">Adjuntos</h4>
            <ul className="mt-1 space-y-1 text-sm text-muted-foreground">
              {documents.map((d) => (
                <li key={d.document_id}>{d.name}</li>
              ))}
            </ul>
          </div>
        )}

        {canViewCommercial && (
          <div>
            <h4 className="text-sm font-medium">Comercial</h4>
            {latestRevision ? (
              <p className="text-sm text-muted-foreground">
                {latestRevision.total_amount} {latestRevision.currency_code} · ronda{' '}
                {latestRevision.round_number} ({latestRevision.round_type})
              </p>
            ) : (
              <p className="text-sm text-muted-foreground">
                Sin montos visibles todavía (esperando apertura de sobres).
              </p>
            )}
          </div>
        )}

        <div className="space-y-2">
          <h4 className="text-sm font-medium">Puntajes</h4>
          {criteria.map((c) => (
            <div key={c.id} className="flex flex-wrap items-center gap-2">
              <span className="min-w-[10rem] text-sm">
                {c.name} <span className="text-xs text-muted-foreground">({c.dimension})</span>
              </span>
              <Input
                type="number"
                min="0"
                max="100"
                disabled={submitted}
                value={scores[c.id]?.score ?? ''}
                onChange={(e) => updateScore(c.id, 'score', e.target.value)}
                className="w-24"
              />
              <Input
                disabled={submitted}
                placeholder="Comentario"
                value={scores[c.id]?.comment ?? ''}
                onChange={(e) => updateScore(c.id, 'comment', e.target.value)}
                className="max-w-xs"
              />
              {!submitted && (
                <Button variant="outline" size="sm" onClick={() => handleSaveScore(c.id)}>
                  Guardar
                </Button>
              )}
            </div>
          ))}
        </div>

        {!submitted && (
          <div className="space-y-2">
            <Textarea
              placeholder="Comentario general (opcional)"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
            />
            <Button onClick={handleSubmit}>Enviar evaluación</Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
