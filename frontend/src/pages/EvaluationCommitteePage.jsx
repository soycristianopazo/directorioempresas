import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useParams } from 'react-router-dom';
import { toast } from 'sonner';
import { ArrowLeft, Save, Users } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { SelectNative } from '@/components/ui/select-native';
import { listTeam } from '@/lib/organizationsApi';
import { getEvent } from '@/lib/sourcingApi';
import {
  listTemplates,
  getSetup,
  applyTemplate,
  listCommittee,
  assignCommittee,
} from '@/lib/evaluationsApi';

const DIMENSIONS = [
  { value: 'TECHNICAL', label: 'Técnica' },
  { value: 'COMMERCIAL', label: 'Comercial' },
  { value: 'HSE', label: 'HSE' },
  { value: 'LEGAL', label: 'Legal' },
  { value: 'FINANCIAL', label: 'Financiera' },
];

export default function EvaluationCommitteePage() {
  const { eventId } = useParams();
  const { activeOrg } = useAuth();
  const [event, setEvent] = useState(null);
  const [team, setTeam] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [setup, setSetup] = useState(null);
  const [templateId, setTemplateId] = useState('');
  const [rows, setRows] = useState({}); // member_id -> { assigned, dimension, canViewCommercial }
  const [loading, setLoading] = useState(true);

  async function load() {
    const [detail, teamRows, templateRows, currentSetup, committee] = await Promise.all([
      getEvent(activeOrg.id, eventId),
      listTeam(activeOrg.id),
      listTemplates(activeOrg.id),
      getSetup(activeOrg.id, eventId),
      listCommittee(activeOrg.id, eventId),
    ]);
    setEvent(detail.event);
    setTeam(teamRows);
    setTemplates(templateRows);
    setSetup(currentSetup);

    const byMember = {};
    for (const a of committee) {
      byMember[a.organization_member_id] = {
        assigned: true,
        dimension: a.dimension,
        canViewCommercial: a.can_view_commercial,
      };
    }
    setRows(byMember);
  }

  useEffect(() => {
    if (!activeOrg) return;
    setLoading(true);
    load().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id, eventId]);

  async function handleApplyTemplate() {
    if (!templateId) return;
    try {
      await applyTemplate(activeOrg.id, eventId, templateId);
      toast.success('Plantilla aplicada al evento');
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo aplicar la plantilla');
    }
  }

  function toggleAssigned(memberId, checked) {
    setRows((prev) => ({
      ...prev,
      [memberId]: checked
        ? { assigned: true, dimension: 'TECHNICAL', canViewCommercial: false }
        : { ...prev[memberId], assigned: false },
    }));
  }

  function updateRow(memberId, field, value) {
    setRows((prev) => ({ ...prev, [memberId]: { ...prev[memberId], [field]: value } }));
  }

  async function handleSaveCommittee() {
    const assignments = Object.entries(rows)
      .filter(([, r]) => r.assigned)
      .map(([memberId, r]) => ({
        organizationMemberId: memberId,
        dimension: r.dimension,
        canViewCommercial: r.canViewCommercial,
      }));
    try {
      await assignCommittee(activeOrg.id, eventId, assignments);
      toast.success('Comité guardado');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo guardar el comité');
    }
  }

  if (!activeOrg || loading || !event) {
    return <div className="h-32 animate-pulse rounded-lg bg-secondary" />;
  }

  return (
    <div className="space-y-6">
      <Helmet>
        <title>Comité de evaluación · Directorio de Empresas</title>
      </Helmet>

      <div>
        <Link
          to={`/empresa/sourcing/${eventId}`}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" />
          Volver al proceso
        </Link>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">Comité de evaluación</h1>
        <p className="mt-1 text-sm text-muted-foreground">{event.name}</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Plantilla de criterios</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {setup ? (
            <p className="text-sm">
              Plantilla aplicada: <span className="font-medium">{setup.template_name_snapshot}</span>{' '}
              ({setup.criteria_snapshot.length} criterio(s))
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">Sin plantilla aplicada todavía.</p>
          )}
          <div className="flex items-center gap-2">
            <SelectNative
              value={templateId}
              onChange={(e) => setTemplateId(e.target.value)}
              className="max-w-xs"
            >
              <option value="">Elegir plantilla…</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </SelectNative>
            <Button variant="outline" onClick={handleApplyTemplate} disabled={!templateId}>
              Aplicar
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center gap-2">
          <Users className="size-4 text-primary" />
          <CardTitle className="text-base">Miembros del comité</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {team.map((m) => {
              const row = rows[m.member_id] || { assigned: false, dimension: 'TECHNICAL', canViewCommercial: false };
              return (
                <div key={m.member_id} className="flex flex-wrap items-center gap-3 rounded-lg border px-3 py-2">
                  <Checkbox
                    checked={row.assigned}
                    onCheckedChange={(checked) => toggleAssigned(m.member_id, checked)}
                  />
                  <span className="min-w-[10rem] text-sm font-medium">{m.full_name}</span>
                  <SelectNative
                    value={row.dimension}
                    onChange={(e) => updateRow(m.member_id, 'dimension', e.target.value)}
                    disabled={!row.assigned}
                    className="w-40"
                  >
                    {DIMENSIONS.map((d) => (
                      <option key={d.value} value={d.value}>
                        {d.label}
                      </option>
                    ))}
                  </SelectNative>
                  <span className="flex items-center gap-1.5 text-sm">
                    <Checkbox
                      checked={row.canViewCommercial}
                      disabled={!row.assigned}
                      onCheckedChange={(checked) => updateRow(m.member_id, 'canViewCommercial', !!checked)}
                    />
                    Ve montos (solo tras apertura)
                  </span>
                </div>
              );
            })}
          </div>
          <Button className="mt-4 gap-1.5" onClick={handleSaveCommittee}>
            <Save className="size-4" />
            Guardar comité
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
