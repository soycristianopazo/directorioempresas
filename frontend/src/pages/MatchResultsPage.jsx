import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { useParams } from 'react-router-dom';
import { toast } from 'sonner';
import { ChevronDown, ChevronUp, Sparkles, Target } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { getEvent } from '@/lib/sourcingApi';
import { getLatestResults, runMatching } from '@/lib/matchingApi';

export default function MatchResultsPage() {
  const { eventId } = useParams();
  const { activeOrg } = useAuth();
  const [event, setEvent] = useState(null);
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [expanded, setExpanded] = useState(null);

  async function loadAll() {
    const detail = await getEvent(activeOrg.id, eventId);
    setEvent(detail.event);
    const latest = await getLatestResults(activeOrg.id, eventId);
    if (latest) {
      setResponse({ ...latest.run, results: latest.results });
    }
  }

  useEffect(() => {
    if (!activeOrg) return;
    setLoading(true);
    loadAll().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id, eventId]);

  async function onRun() {
    setRunning(true);
    try {
      const result = await runMatching(activeOrg.id, eventId);
      setResponse(result);
      toast.success(`${result.eligible_count} proveedores elegibles de ${result.candidates_evaluated} evaluados`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo correr el matching');
    } finally {
      setRunning(false);
    }
  }

  if (!activeOrg || loading) return <div className="h-32 animate-pulse rounded-lg bg-secondary" />;

  const results = response?.results || [];
  const eligible = results.filter((r) => r.is_eligible).sort((a, b) => (a.rank || 999) - (b.rank || 999));
  const almostEligible = results.filter((r) => !r.is_eligible);

  return (
    <div className="space-y-8">
      <Helmet>
        <title>Resultados de matching · Directorio de Empresas</title>
      </Helmet>

      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Resultados de matching</h1>
          <p className="mt-1 text-sm text-muted-foreground">{event?.name}</p>
        </div>
        <Button onClick={onRun} disabled={running}>
          <Sparkles className="size-4" />
          {running ? 'Calculando…' : 'Correr matching'}
        </Button>
      </header>

      {response && (
        <p className="text-sm text-muted-foreground">
          {response.eligible_count} elegibles de {response.candidates_evaluated} evaluados · motor{' '}
          {response.engine_version}
        </p>
      )}

      {eligible.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="size-4 text-primary" />
              Elegibles, ordenados por puntaje
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {eligible.map((r) => (
              <ResultRow
                key={r.offering_id}
                result={r}
                expanded={expanded === r.offering_id}
                onToggle={() => setExpanded(expanded === r.offering_id ? null : r.offering_id)}
              />
            ))}
          </CardContent>
        </Card>
      )}

      {almostEligible.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Casi elegibles</CardTitle>
            <CardDescription>Cumplen parte de los requisitos, pero no todos los MUST.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {almostEligible.map((r) => (
              <div key={r.offering_id} className="rounded-lg border px-3 py-2 text-sm">
                <ul className="mt-1 list-disc pl-4 text-xs text-muted-foreground">
                  {r.blocking_reasons.map((reason, i) => (
                    <li key={i}>{reason}</li>
                  ))}
                </ul>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {response && eligible.length === 0 && almostEligible.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No hay candidatos que coincidan con la categoría de este proceso todavía.
        </p>
      )}
    </div>
  );
}

const COMPONENT_LABELS = {
  category_fit: 'Categoría',
  attribute_fit: 'Atributos técnicos',
  territory_fit: 'Cobertura territorial',
  experience_fit: 'Experiencia',
  accreditation_fit: 'Acreditación',
  performance_fit: 'Desempeño',
  responsiveness_fit: 'Nivel de respuesta',
  capacity_fit: 'Capacidad',
};

function ResultRow({ result, expanded, onToggle }) {
  const breakdown = result.score_breakdown;
  return (
    <div className="rounded-lg border px-3 py-2 text-sm">
      <button type="button" onClick={onToggle} className="flex w-full items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Badge>#{result.rank}</Badge>
          <span className="font-mono text-xs text-muted-foreground">
            {result.offering_id.slice(0, 8)}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-semibold">{result.total_score.toFixed(1)}</span>
          {expanded ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
        </div>
      </button>

      {expanded && breakdown?.components && (
        <div className="mt-3 space-y-2 border-t pt-3">
          {breakdown.components.map((c) => (
            <div key={c.key} className="flex items-center justify-between text-xs">
              <span>
                {COMPONENT_LABELS[c.key] || c.key} ({c.weight})
              </span>
              <span className="text-muted-foreground">
                {c.points} pts — {c.detail}
              </span>
            </div>
          ))}
          {breakdown.modifiers?.length > 0 && (
            <div className="border-t pt-2 text-xs text-muted-foreground">
              {breakdown.modifiers.map((m) => (
                <div key={m.key}>
                  {m.label} ×{m.factor}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
