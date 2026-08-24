import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useParams } from 'react-router-dom';
import { toast } from 'sonner';
import { ClipboardCheck, FileSearch, Plus, Trash2 } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { SelectNative } from '@/components/ui/select-native';
import { CategorySelector } from '@/components/CategorySelector';
import { getCertificationTypes } from '@/lib/credentialsApi';
import { listPrograms } from '@/lib/accreditationApi';
import { getIndustries } from '@/lib/taxonomyApi';
import { getAdminDivisions } from '@/lib/referenceApi';
import { addCriterion, addItem, deleteCriterion, getEvent, publishEvent } from '@/lib/sourcingApi';

const CRITERION_TYPES = [
  { value: 'ACCREDITATION', label: 'Acreditación' },
  { value: 'CERTIFICATION', label: 'Certificación' },
  { value: 'TERRITORY', label: 'Cobertura territorial' },
  { value: 'EXPERIENCE_YEARS', label: 'Años de experiencia' },
  { value: 'INDUSTRY_EXPERIENCE', label: 'Experiencia en industria' },
  { value: 'CAPACITY', label: 'Capacidad' },
  { value: 'CUSTOM', label: 'Otro (informativo)' },
];

export default function SourcingEventDetailPage() {
  const { eventId } = useParams();
  const { activeOrg } = useAuth();
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);

  async function loadAll() {
    setDetail(await getEvent(activeOrg.id, eventId));
  }

  useEffect(() => {
    if (!activeOrg) return;
    setLoading(true);
    loadAll().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id, eventId]);

  async function onPublish() {
    try {
      await publishEvent(activeOrg.id, eventId);
      toast.success('Proceso publicado');
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo publicar');
    }
  }

  if (!activeOrg || loading || !detail) {
    return <div className="h-32 animate-pulse rounded-lg bg-secondary" />;
  }

  const { event, items, criteria } = detail;
  const isDraft = event.status === 'DRAFT';

  return (
    <div className="space-y-8">
      <Helmet>
        <title>{event.name} · Directorio de Empresas</title>
      </Helmet>

      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{event.name}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {event.event_code} · {items.length} línea(s) · {criteria.length} criterio(s)
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline">{event.status}</Badge>
          {isDraft && <Button onClick={onPublish}>Publicar</Button>}
          <Link to={`/empresa/sourcing/${eventId}/resultados`}>
            <Button variant="outline">
              <FileSearch className="size-4" />
              Ver matches
            </Button>
          </Link>
        </div>
      </header>

      <ItemsCard organizationId={activeOrg.id} eventId={eventId} items={items} onChanged={loadAll} />
      <CriteriaCard
        organizationId={activeOrg.id}
        eventId={eventId}
        criteria={criteria}
        onChanged={loadAll}
      />
    </div>
  );
}

function ItemsCard({ organizationId, eventId, items, onChanged }) {
  const [description, setDescription] = useState('');
  const [quantity, setQuantity] = useState('');
  const [taxonomyNodes, setTaxonomyNodes] = useState([]);

  async function onAdd() {
    if (!description || !quantity) return;
    try {
      await addItem(organizationId, eventId, {
        description,
        quantity: Number(quantity),
        taxonomyNodeId: taxonomyNodes[0]?.node_id,
      });
      toast.success('Línea agregada');
      setDescription('');
      setQuantity('');
      setTaxonomyNodes([]);
      await onChanged();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo agregar la línea');
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ClipboardCheck className="size-4 text-primary" />
          Líneas a cotizar
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <ul className="space-y-2">
          {items.map((item) => (
            <li key={item.id} className="rounded-lg border px-3 py-2 text-sm">
              {item.description} — {item.quantity} {item.unit_code || ''}
            </li>
          ))}
          {items.length === 0 && (
            <p className="text-sm text-muted-foreground">Sin líneas todavía.</p>
          )}
        </ul>

        <div className="space-y-3 border-t pt-4">
          <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
            <div className="space-y-1.5">
              <Label htmlFor="item-description">Descripción</Label>
              <Input
                id="item-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="item-quantity">Cantidad</Label>
              <Input
                id="item-quantity"
                type="number"
                min={1}
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
              />
            </div>
          </div>
          <div>
            <p className="mb-1.5 text-xs font-medium text-muted-foreground">
              Categoría (opcional, guía el matching)
            </p>
            <CategorySelector selected={taxonomyNodes} onChange={setTaxonomyNodes} allowPrimary={false} />
          </div>
          <Button size="sm" onClick={onAdd}>
            <Plus className="size-4" />
            Agregar línea
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

const emptyCriterionForm = {
  criterionType: 'ACCREDITATION',
  requirementLevel: 'MUST_HAVE',
  description: '',
  accreditationProgramId: '',
  certificationTypeId: '',
  adminDivisionId: '',
  maxMobilizationDays: '',
  industryId: '',
  minYears: '',
  minCapacity: '',
};

function CriteriaCard({ organizationId, eventId, criteria, onChanged }) {
  const [form, setForm] = useState(emptyCriterionForm);
  const [programs, setPrograms] = useState([]);
  const [certTypes, setCertTypes] = useState([]);
  const [industries, setIndustries] = useState([]);
  const [divisions, setDivisions] = useState([]);

  useEffect(() => {
    listPrograms().then(setPrograms);
    getCertificationTypes().then(setCertTypes);
    getIndustries().then(setIndustries);
    getAdminDivisions({ country: 'CL' }).then(setDivisions);
  }, []);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function onAdd() {
    try {
      await addCriterion(organizationId, eventId, {
        criterionType: form.criterionType,
        requirementLevel: form.requirementLevel,
        description: form.description || null,
        accreditationProgramId: form.accreditationProgramId || undefined,
        certificationTypeId: form.certificationTypeId || undefined,
        adminDivisionId: form.adminDivisionId || undefined,
        maxMobilizationDays: form.maxMobilizationDays ? Number(form.maxMobilizationDays) : undefined,
        industryId: form.industryId || undefined,
        minYears: form.minYears ? Number(form.minYears) : undefined,
        minCapacity: form.minCapacity ? Number(form.minCapacity) : undefined,
      });
      toast.success('Criterio agregado');
      setForm(emptyCriterionForm);
      await onChanged();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo agregar el criterio');
    }
  }

  async function onDelete(criterionId) {
    try {
      await deleteCriterion(organizationId, eventId, criterionId);
      await onChanged();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo eliminar');
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Criterios MUST / NICE</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <ul className="space-y-2">
          {criteria.map((c) => (
            <li
              key={c.id}
              className="flex items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm"
            >
              <div>
                <Badge variant="outline" className="mr-2">
                  {c.requirement_level === 'MUST_HAVE' ? 'MUST' : 'NICE'}
                </Badge>
                {CRITERION_TYPES.find((t) => t.value === c.criterion_type)?.label}
                {c.description && <span className="ml-2 text-muted-foreground">{c.description}</span>}
              </div>
              <Button variant="ghost" size="sm" onClick={() => onDelete(c.id)}>
                <Trash2 className="size-3.5" />
              </Button>
            </li>
          ))}
          {criteria.length === 0 && (
            <p className="text-sm text-muted-foreground">Sin criterios todavía.</p>
          )}
        </ul>

        <div className="grid gap-3 border-t pt-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label>Tipo de criterio</Label>
            <SelectNative
              value={form.criterionType}
              onChange={(e) => update('criterionType', e.target.value)}
            >
              {CRITERION_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </SelectNative>
          </div>
          <div className="space-y-1.5">
            <Label>Nivel</Label>
            <SelectNative
              value={form.requirementLevel}
              onChange={(e) => update('requirementLevel', e.target.value)}
            >
              <option value="MUST_HAVE">MUST — obligatorio</option>
              <option value="NICE_TO_HAVE">NICE — deseable</option>
            </SelectNative>
          </div>

          {form.criterionType === 'ACCREDITATION' && (
            <div className="space-y-1.5 sm:col-span-2">
              <Label>Programa exigido</Label>
              <SelectNative
                value={form.accreditationProgramId}
                onChange={(e) => update('accreditationProgramId', e.target.value)}
              >
                <option value="">Selecciona…</option>
                {programs.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </SelectNative>
            </div>
          )}

          {form.criterionType === 'CERTIFICATION' && (
            <div className="space-y-1.5 sm:col-span-2">
              <Label>Certificación exigida</Label>
              <SelectNative
                value={form.certificationTypeId}
                onChange={(e) => update('certificationTypeId', e.target.value)}
              >
                <option value="">Selecciona…</option>
                {certTypes.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </SelectNative>
            </div>
          )}

          {form.criterionType === 'TERRITORY' && (
            <>
              <div className="space-y-1.5">
                <Label>Comuna/división exigida</Label>
                <SelectNative
                  value={form.adminDivisionId}
                  onChange={(e) => update('adminDivisionId', e.target.value)}
                >
                  <option value="">Selecciona…</option>
                  {divisions.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </SelectNative>
              </div>
              <div className="space-y-1.5">
                <Label>Días máx. de movilización (opcional)</Label>
                <Input
                  type="number"
                  min={0}
                  value={form.maxMobilizationDays}
                  onChange={(e) => update('maxMobilizationDays', e.target.value)}
                />
              </div>
            </>
          )}

          {form.criterionType === 'EXPERIENCE_YEARS' && (
            <div className="space-y-1.5">
              <Label>Años mínimos</Label>
              <Input
                type="number"
                min={1}
                value={form.minYears}
                onChange={(e) => update('minYears', e.target.value)}
              />
            </div>
          )}

          {form.criterionType === 'INDUSTRY_EXPERIENCE' && (
            <>
              <div className="space-y-1.5">
                <Label>Industria</Label>
                <SelectNative
                  value={form.industryId}
                  onChange={(e) => update('industryId', e.target.value)}
                >
                  <option value="">Selecciona…</option>
                  {industries.map((i) => (
                    <option key={i.id} value={i.id}>
                      {i.name}
                    </option>
                  ))}
                </SelectNative>
              </div>
              <div className="space-y-1.5">
                <Label>Años mínimos en esa industria</Label>
                <Input
                  type="number"
                  min={1}
                  value={form.minYears}
                  onChange={(e) => update('minYears', e.target.value)}
                />
              </div>
            </>
          )}

          {form.criterionType === 'CAPACITY' && (
            <div className="space-y-1.5">
              <Label>Capacidad mensual mínima</Label>
              <Input
                type="number"
                min={1}
                value={form.minCapacity}
                onChange={(e) => update('minCapacity', e.target.value)}
              />
            </div>
          )}

          <div className="space-y-1.5 sm:col-span-2">
            <Label>Nota (obligatoria para &quot;Otro&quot;)</Label>
            <Input value={form.description} onChange={(e) => update('description', e.target.value)} />
          </div>

          <div>
            <Button size="sm" onClick={onAdd}>
              <Plus className="size-4" />
              Agregar criterio
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
