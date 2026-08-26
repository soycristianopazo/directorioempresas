import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { useOutletContext, useParams } from 'react-router-dom';
import { toast } from 'sonner';
import {
  Ban,
  ClipboardCheck,
  Factory,
  HelpCircle,
  Lock,
  MapPinned,
  Plus,
  Receipt,
  Send,
  ShieldCheck,
  Tags,
  Trash2,
  Unlock,
  UserPlus,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { SelectNative } from '@/components/ui/select-native';
import { Textarea } from '@/components/ui/textarea';
import { AdminDivisionSelector } from '@/components/AdminDivisionSelector';
import { SingleTreePicker } from '@/components/SingleTreePicker';
import { ConversationPanel } from '@/components/ConversationPanel';
import { getCertificationTypes } from '@/lib/credentialsApi';
import { listPrograms } from '@/lib/accreditationApi';
import { getTaxonomyTree, getIndustries } from '@/lib/taxonomyApi';
import { getAdminDivisions } from '@/lib/referenceApi';
import {
  getRequirement,
  updateRequirement,
  addRequirementLocation,
  removeRequirementLocation,
} from '@/lib/requirementsApi';
import { addCriterion, addItem, deleteCriterion, updateEvent } from '@/lib/sourcingApi';
import { disqualifyInvitation, inviteSupplier, listInvitations } from '@/lib/invitationsApi';
import { answerQuestion, listQuestions, publishAnswer } from '@/lib/qaApi';
import { listQuotations, openBids } from '@/lib/quotationsApi';

const INVITATION_STATUS_LABELS = {
  INVITED: 'Invitado',
  VIEWED: 'Vista',
  NDA_ACCEPTED: 'NDA aceptado',
  INTERESTED: 'Interesado',
  PARTICIPATING: 'Participando',
  QUOTED: 'Cotización enviada',
  DECLINED: 'Declinado',
  NO_RESPONSE: 'Sin respuesta',
  WITHDRAWN: 'Retirado',
  DISQUALIFIED: 'Descalificado',
  EXPIRED: 'Expirado',
};

const INVITATION_STATUS_VARIANT = {
  INVITED: 'neutral',
  VIEWED: 'neutral',
  NDA_ACCEPTED: 'brand',
  INTERESTED: 'brand',
  PARTICIPATING: 'success',
  QUOTED: 'success',
  DECLINED: 'destructive',
  WITHDRAWN: 'destructive',
  DISQUALIFIED: 'destructive',
  NO_RESPONSE: 'warning',
  EXPIRED: 'warning',
};

const TERMINAL_INVITATION_STATUSES = new Set([
  'DECLINED',
  'WITHDRAWN',
  'DISQUALIFIED',
  'NO_RESPONSE',
  'EXPIRED',
]);

const PARTICIPATING_INVITATION_STATUSES = new Set(['PARTICIPATING', 'QUOTED']);

function formatDateTime(value) {
  if (!value) return '—';
  return new Intl.DateTimeFormat('es-CL', { dateStyle: 'medium', timeStyle: 'short' }).format(
    new Date(value),
  );
}

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
  // El layout (SourcingEventLayout) ya trae event/items/criteria en una
  // sola consulta compartida por todas las pestañas — pedirlo de nuevo acá
  // duplicaba la llamada más pesada del workspace en cada carga.
  const { event, items, criteria, reloadEvent } = useOutletContext();
  const [invitations, setInvitations] = useState([]);
  const [loadingInvitations, setLoadingInvitations] = useState(true);

  async function loadInvitations() {
    try {
      if (event.status === 'PUBLISHED') {
        setInvitations(await listInvitations(activeOrg.id, eventId));
      } else {
        setInvitations([]);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudieron cargar las invitaciones');
    }
  }

  useEffect(() => {
    if (!activeOrg) return;
    setLoadingInvitations(true);
    loadInvitations().finally(() => setLoadingInvitations(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id, eventId, event.status]);

  async function loadAll() {
    // reloadEvent y loadInvitations no dependen entre sí (loadInvitations lee
    // el `event.status` ya renderizado, no el que reloadEvent está por
    // traer) — esperarlas en serie solo sumaba latencia cada vez que se
    // agregaba un ítem/criterio/invitación.
    await Promise.all([reloadEvent(), loadInvitations()]);
  }

  if (!activeOrg || loadingInvitations) {
    return <div className="h-32 animate-pulse rounded-lg bg-secondary" />;
  }

  const isDraft = event.status === 'DRAFT';

  return (
    <div className="space-y-8">
      <Helmet>
        <title>{event.name} · Directorio de Empresas</title>
      </Helmet>

      <p className="text-sm text-muted-foreground">
        {items.length} línea(s) · {criteria.length} criterio(s)
      </p>

      <AccreditationRequirementCard
        organizationId={activeOrg.id}
        eventId={eventId}
        event={event}
        isDraft={isDraft}
        onChanged={loadAll}
      />
      {event.requirement_id && (
        <MatchingGuidanceCard
          organizationId={activeOrg.id}
          requirementId={event.requirement_id}
          isDraft={isDraft}
        />
      )}
      <ItemsCard organizationId={activeOrg.id} eventId={eventId} items={items} onChanged={loadAll} />
      <CriteriaCard
        organizationId={activeOrg.id}
        eventId={eventId}
        criteria={criteria}
        onChanged={loadAll}
      />

      {event.status === 'PUBLISHED' && (
        <>
          <InvitationsCard
            organizationId={activeOrg.id}
            eventId={eventId}
            invitations={invitations}
            onChanged={loadAll}
          />
          <QuestionsCard organizationId={activeOrg.id} eventId={eventId} />
          <QuotationsCard organizationId={activeOrg.id} eventId={eventId} event={event} />
          <ConversationPanel
            organizationId={activeOrg.id}
            contextType="SOURCING_EVENT"
            contextId={eventId}
            participantOrganizationIds={invitations
              .filter((i) => PARTICIPATING_INVITATION_STATUSES.has(i.status))
              .map((i) => i.supplier_organization_id)}
          />
        </>
      )}
    </div>
  );
}

function AccreditationRequirementCard({ organizationId, eventId, event, isDraft, onChanged }) {
  const [programs, setPrograms] = useState([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    listPrograms({ forOrganizationId: organizationId })
      .then(setPrograms)
      .catch((error) => {
        toast.error(error.response?.data?.detail || 'No se pudieron cargar los programas');
      });
  }, [organizationId]);

  const platformProgram = programs.find((p) => p.owner_scope === 'PLATFORM');
  const required = !!event.requires_accreditation_program_id;

  async function onSelect(nextRequired) {
    if (nextRequired === required || saving) return;
    if (nextRequired && !platformProgram) {
      toast.error('No hay un programa de acreditación de plataforma configurado');
      return;
    }
    setSaving(true);
    try {
      await updateEvent(organizationId, eventId, event, {
        requires_accreditation_program_id: nextRequired ? platformProgram.id : null,
      });
      toast.success('Requisito de acreditación actualizado');
      await onChanged();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo actualizar el requisito');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ShieldCheck className="size-4 text-primary" />
          Requisito de acreditación
        </CardTitle>
      </CardHeader>
      <CardContent className="flex items-center gap-2">
        <Button
          type="button"
          size="sm"
          variant={required ? 'default' : 'outline'}
          disabled={!isDraft || saving}
          onClick={() => onSelect(true)}
        >
          Acreditado
        </Button>
        <Button
          type="button"
          size="sm"
          variant={!required ? 'default' : 'outline'}
          disabled={!isDraft || saving}
          onClick={() => onSelect(false)}
        >
          No acreditado
        </Button>
      </CardContent>
    </Card>
  );
}

/** Categoría + Industria + Territorio agrupados como en CompanyCoveragePage
 * ("Cobertura e industrias") — las tres viven en la necesidad ligada al
 * evento (`requirements`), no en el evento mismo: Categoría/Industria son
 * selectores en cascada de un solo valor (mismo componente que usa la
 * creación de la publicación), Territorio reusa AdminDivisionSelector +
 * chips removibles igual que Cobertura. */
function MatchingGuidanceCard({ organizationId, requirementId, isDraft }) {
  const [requirement, setRequirement] = useState(null);
  const [locations, setLocations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  async function load() {
    try {
      const detail = await getRequirement(organizationId, requirementId);
      setRequirement(detail.requirement);
      setLocations(detail.locations);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo cargar la cobertura de la necesidad');
    }
  }

  useEffect(() => {
    setLoading(true);
    load().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [organizationId, requirementId]);

  async function save(overrides) {
    setSaving(true);
    try {
      await updateRequirement(organizationId, requirementId, requirement, overrides);
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo actualizar');
    } finally {
      setSaving(false);
    }
  }

  async function handleAddLocation(adminDivisionId) {
    try {
      await addRequirementLocation(organizationId, requirementId, adminDivisionId);
      toast.success('Cobertura agregada');
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo agregar');
    }
  }

  async function handleRemoveLocation(locationId) {
    try {
      await removeRequirementLocation(organizationId, requirementId, locationId);
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo eliminar');
    }
  }

  if (loading || !requirement) {
    return <div className="h-32 animate-pulse rounded-lg bg-secondary" />;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Tags className="size-4 text-primary" />
          Categoría, industria y territorio
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <p className="text-xs text-muted-foreground">
          Opcional — mientras más completo, mejor el match por experiencia y cobertura.
        </p>

        <div className="space-y-1.5">
          <Label className="flex items-center gap-1.5">
            <Tags className="size-3.5" />
            Categoría
          </Label>
          <SingleTreePicker
            loader={getTaxonomyTree}
            value={requirement.primary_taxonomy_node_id}
            onChange={(id) => save({ primary_taxonomy_node_id: id })}
            placeholder="Cualquiera"
            subPlaceholder="Subcategoría (opcional)"
          />
        </div>

        <div className="space-y-1.5 border-t pt-4">
          <Label className="flex items-center gap-1.5">
            <Factory className="size-3.5" />
            Industria
          </Label>
          <SingleTreePicker
            loader={getIndustries}
            value={requirement.industry_id}
            onChange={(id) => save({ industry_id: id })}
            placeholder="Cualquiera"
            subPlaceholder="Subindustria (opcional)"
          />
        </div>

        <div className="space-y-2 border-t pt-4">
          <Label className="flex items-center gap-1.5">
            <MapPinned className="size-3.5" />
            Territorio ({locations.length})
          </Label>
          <div className="flex flex-wrap gap-2">
            {locations.map((l) => (
              <Badge key={l.id} variant="neutral" className="gap-1.5">
                {l.name}
                {isDraft && (
                  <button onClick={() => handleRemoveLocation(l.id)} aria-label={`Quitar ${l.name}`}>
                    <Trash2 className="size-3" />
                  </button>
                )}
              </Badge>
            ))}
            {locations.length === 0 && (
              <p className="text-sm text-muted-foreground">Sin cobertura declarada.</p>
            )}
          </div>
          {isDraft && <AdminDivisionSelector onAdd={handleAddLocation} disabled={saving} />}
        </div>
      </CardContent>
    </Card>
  );
}

function ItemsCard({ organizationId, eventId, items, onChanged }) {
  const [description, setDescription] = useState('');
  const [quantity, setQuantity] = useState('');

  async function onAdd() {
    if (!description || !quantity) return;
    try {
      await addItem(organizationId, eventId, {
        description,
        quantity: Number(quantity),
      });
      toast.success('Línea agregada');
      setDescription('');
      setQuantity('');
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

        <div className="grid gap-3 border-t pt-4 sm:grid-cols-[1fr_auto]">
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
          <div className="sm:col-span-2">
            <Button size="sm" onClick={onAdd}>
              <Plus className="size-4" />
              Agregar línea
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function emptyEntry() {
  return {
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
}

/** Antes elegía un solo tipo de criterio a la vez ("Tipo de criterio" en
 * SelectNative); ahora los tipos son checkboxes y cada uno marcado abre su
 * propia mini-ficha con su Nivel (MUST/NICE) y sus campos específicos —
 * "Agregar criterios" llama addCriterion() una vez por tipo marcado. */
function CriteriaCard({ organizationId, eventId, criteria, onChanged }) {
  const [entries, setEntries] = useState({});
  const [programs, setPrograms] = useState([]);
  const [certTypes, setCertTypes] = useState([]);
  const [industries, setIndustries] = useState([]);
  const [divisions, setDivisions] = useState([]);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    listPrograms()
      .then(setPrograms)
      .catch((error) => {
        toast.error(error.response?.data?.detail || 'No se pudieron cargar los programas');
      });
    getCertificationTypes()
      .then(setCertTypes)
      .catch((error) => {
        toast.error(error.response?.data?.detail || 'No se pudieron cargar las certificaciones');
      });
    getIndustries()
      .then(setIndustries)
      .catch((error) => {
        toast.error(error.response?.data?.detail || 'No se pudieron cargar las industrias');
      });
    getAdminDivisions({ country: 'CL' })
      .then(setDivisions)
      .catch((error) => {
        toast.error(error.response?.data?.detail || 'No se pudieron cargar las divisiones administrativas');
      });
  }, []);

  function toggleType(type, checked) {
    setEntries((prev) => {
      const next = { ...prev };
      if (checked) next[type] = emptyEntry();
      else delete next[type];
      return next;
    });
  }

  function updateEntry(type, field, value) {
    setEntries((prev) => ({ ...prev, [type]: { ...prev[type], [field]: value } }));
  }

  const types = Object.keys(entries);

  async function onAdd() {
    if (types.length === 0) return;
    setSubmitting(true);
    try {
      for (const type of types) {
        const f = entries[type];
        await addCriterion(organizationId, eventId, {
          criterionType: type,
          requirementLevel: f.requirementLevel,
          description: f.description || null,
          accreditationProgramId: f.accreditationProgramId || undefined,
          certificationTypeId: f.certificationTypeId || undefined,
          adminDivisionId: f.adminDivisionId || undefined,
          maxMobilizationDays: f.maxMobilizationDays ? Number(f.maxMobilizationDays) : undefined,
          industryId: f.industryId || undefined,
          minYears: f.minYears ? Number(f.minYears) : undefined,
          minCapacity: f.minCapacity ? Number(f.minCapacity) : undefined,
        });
      }
      toast.success(types.length > 1 ? 'Criterios agregados' : 'Criterio agregado');
      setEntries({});
      await onChanged();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo agregar el criterio');
    } finally {
      setSubmitting(false);
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
                <Badge variant="neutral" className="mr-2">
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

        <div className="space-y-3 border-t pt-4">
          <Label>Tipo de criterio (puedes elegir más de uno)</Label>
          <div className="grid gap-2 sm:grid-cols-2">
            {CRITERION_TYPES.map((t) => (
              <label
                key={t.value}
                className="flex items-center gap-2 rounded-lg border px-3 py-2 text-sm"
              >
                <Checkbox
                  checked={!!entries[t.value]}
                  onCheckedChange={(checked) => toggleType(t.value, !!checked)}
                />
                {t.label}
              </label>
            ))}
          </div>

          {types.length > 0 && (
            <div className="space-y-3">
              {types.map((type) => {
                const f = entries[type];
                return (
                  <div key={type} className="space-y-3 rounded-lg border p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-sm font-medium">
                        {CRITERION_TYPES.find((t) => t.value === type)?.label}
                      </span>
                      <SelectNative
                        className="w-52"
                        value={f.requirementLevel}
                        onChange={(e) => updateEntry(type, 'requirementLevel', e.target.value)}
                      >
                        <option value="MUST_HAVE">MUST — obligatorio</option>
                        <option value="NICE_TO_HAVE">NICE — deseable</option>
                      </SelectNative>
                    </div>

                    {type === 'ACCREDITATION' && (
                      <div className="space-y-1.5">
                        <Label>Programa exigido</Label>
                        <SelectNative
                          value={f.accreditationProgramId}
                          onChange={(e) => updateEntry(type, 'accreditationProgramId', e.target.value)}
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

                    {type === 'CERTIFICATION' && (
                      <div className="space-y-1.5">
                        <Label>Certificación exigida</Label>
                        <SelectNative
                          value={f.certificationTypeId}
                          onChange={(e) => updateEntry(type, 'certificationTypeId', e.target.value)}
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

                    {type === 'TERRITORY' && (
                      <div className="grid gap-3 sm:grid-cols-2">
                        <div className="space-y-1.5">
                          <Label>Comuna/división exigida</Label>
                          <SelectNative
                            value={f.adminDivisionId}
                            onChange={(e) => updateEntry(type, 'adminDivisionId', e.target.value)}
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
                            value={f.maxMobilizationDays}
                            onChange={(e) => updateEntry(type, 'maxMobilizationDays', e.target.value)}
                          />
                        </div>
                      </div>
                    )}

                    {type === 'EXPERIENCE_YEARS' && (
                      <div className="space-y-1.5">
                        <Label>Años mínimos</Label>
                        <Input
                          type="number"
                          min={1}
                          value={f.minYears}
                          onChange={(e) => updateEntry(type, 'minYears', e.target.value)}
                        />
                      </div>
                    )}

                    {type === 'INDUSTRY_EXPERIENCE' && (
                      <div className="grid gap-3 sm:grid-cols-2">
                        <div className="space-y-1.5">
                          <Label>Industria</Label>
                          <SelectNative
                            value={f.industryId}
                            onChange={(e) => updateEntry(type, 'industryId', e.target.value)}
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
                            value={f.minYears}
                            onChange={(e) => updateEntry(type, 'minYears', e.target.value)}
                          />
                        </div>
                      </div>
                    )}

                    {type === 'CAPACITY' && (
                      <div className="space-y-1.5">
                        <Label>Capacidad mensual mínima</Label>
                        <Input
                          type="number"
                          min={1}
                          value={f.minCapacity}
                          onChange={(e) => updateEntry(type, 'minCapacity', e.target.value)}
                        />
                      </div>
                    )}

                    <div className="space-y-1.5">
                      <Label>Nota {type === 'CUSTOM' ? '(obligatoria)' : '(opcional)'}</Label>
                      <Input
                        value={f.description}
                        onChange={(e) => updateEntry(type, 'description', e.target.value)}
                      />
                    </div>
                  </div>
                );
              })}

              <Button size="sm" onClick={onAdd} disabled={submitting}>
                <Plus className="size-4" />
                {types.length > 1 ? 'Agregar criterios' : 'Agregar criterio'}
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function InvitationsCard({ organizationId, eventId, invitations, onChanged }) {
  const [supplierOrganizationId, setSupplierOrganizationId] = useState('');
  const [inviting, setInviting] = useState(false);

  async function onInvite() {
    if (!supplierOrganizationId.trim()) return;
    setInviting(true);
    try {
      await inviteSupplier(organizationId, eventId, {
        supplierOrganizationId: supplierOrganizationId.trim(),
      });
      toast.success('Proveedor invitado');
      setSupplierOrganizationId('');
      await onChanged();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo invitar al proveedor');
    } finally {
      setInviting(false);
    }
  }

  async function onDisqualify(invitationId) {
    const reason = window.prompt('Motivo de descalificación (opcional)');
    if (reason === null) return;
    try {
      await disqualifyInvitation(organizationId, eventId, invitationId, reason || null);
      toast.success('Invitación descalificada');
      await onChanged();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo descalificar');
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <UserPlus className="size-4 text-primary" />
          Proveedores invitados ({invitations.length})
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <ul className="space-y-2">
          {invitations.map((inv) => (
            <li
              key={inv.id}
              className="flex items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm"
            >
              <div>
                <span className="font-mono text-xs text-muted-foreground">
                  {inv.supplier_organization_id}
                </span>
                <Badge
                  variant={INVITATION_STATUS_VARIANT[inv.status] || 'neutral'}
                  className="ml-2"
                >
                  {INVITATION_STATUS_LABELS[inv.status] || inv.status}
                </Badge>
                <span className="ml-2 text-xs text-muted-foreground">
                  invitado {formatDateTime(inv.invited_at)}
                </span>
              </div>
              {!TERMINAL_INVITATION_STATUSES.has(inv.status) && (
                <Button variant="ghost" size="sm" onClick={() => onDisqualify(inv.id)}>
                  <Ban className="size-3.5" />
                  Descalificar
                </Button>
              )}
            </li>
          ))}
          {invitations.length === 0 && (
            <p className="text-sm text-muted-foreground">Aún no invitas proveedores.</p>
          )}
        </ul>

        <div className="flex items-end gap-2 border-t pt-4">
          <div className="flex-1 space-y-1.5">
            <Label htmlFor="supplier-org-id">ID de organización proveedora</Label>
            <Input
              id="supplier-org-id"
              placeholder="UUID de la organización"
              value={supplierOrganizationId}
              onChange={(e) => setSupplierOrganizationId(e.target.value)}
            />
          </div>
          <Button size="sm" onClick={onInvite} disabled={inviting}>
            <Send className="size-4" />
            Invitar
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

const QA_VISIBILITY_OPTIONS = [
  { value: 'ALL_PARTICIPANTS', label: 'Visible para todos los participantes' },
  { value: 'PRIVATE_TO_ASKER', label: 'Solo visible para quien preguntó' },
];

function QuestionsCard({ organizationId, eventId }) {
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [answerDrafts, setAnswerDrafts] = useState({});

  async function loadQuestions() {
    try {
      setQuestions(await listQuestions(organizationId, eventId));
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudieron cargar las preguntas');
    }
  }

  useEffect(() => {
    setLoading(true);
    loadQuestions().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [organizationId, eventId]);

  function draftFor(questionId) {
    return answerDrafts[questionId] || { body: '', visibility: 'ALL_PARTICIPANTS' };
  }

  function updateDraft(questionId, field, value) {
    setAnswerDrafts((prev) => ({
      ...prev,
      [questionId]: { ...draftFor(questionId), [field]: value },
    }));
  }

  async function onAnswer(question) {
    const draft = draftFor(question.id);
    if (!draft.body.trim()) return;
    try {
      await answerQuestion(organizationId, eventId, question.id, draft.body.trim(), draft.visibility);
      toast.success('Respuesta enviada');
      setAnswerDrafts((prev) => {
        const next = { ...prev };
        delete next[question.id];
        return next;
      });
      await loadQuestions();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo responder');
    }
  }

  async function onPublish(question) {
    try {
      await publishAnswer(organizationId, eventId, question.id);
      toast.success('Respuesta publicada');
      await loadQuestions();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo publicar la respuesta');
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <HelpCircle className="size-4 text-primary" />
          Preguntas y respuestas
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {loading ? (
          <div className="h-16 animate-pulse rounded-lg bg-secondary" />
        ) : (
          <>
            {questions.map((q) => (
              <div key={q.id} className="space-y-2 rounded-lg border px-3 py-2 text-sm">
                <div>
                  <p>{q.body}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {q.asked_by_organization_id} · {formatDateTime(q.asked_at)}
                  </p>
                </div>

                {q.answer_body ? (
                  <div className="rounded-lg bg-secondary/60 px-3 py-2">
                    <p>{q.answer_body}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {formatDateTime(q.answered_at)}
                      {q.answer_visibility === 'PRIVATE_TO_ASKER' && ' · solo para quien preguntó'}
                    </p>
                    {!q.published_at && (
                      <Button
                        size="sm"
                        variant="outline"
                        className="mt-2"
                        onClick={() => onPublish(q)}
                      >
                        Publicar respuesta
                      </Button>
                    )}
                  </div>
                ) : (
                  <div className="space-y-2 border-t pt-2">
                    <Textarea
                      placeholder="Escribe una respuesta…"
                      value={draftFor(q.id).body}
                      onChange={(e) => updateDraft(q.id, 'body', e.target.value)}
                    />
                    <div className="flex items-center gap-2">
                      <SelectNative
                        className="max-w-xs"
                        value={draftFor(q.id).visibility}
                        onChange={(e) => updateDraft(q.id, 'visibility', e.target.value)}
                      >
                        {QA_VISIBILITY_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </SelectNative>
                      <Button size="sm" onClick={() => onAnswer(q)}>
                        Responder
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            ))}
            {questions.length === 0 && (
              <p className="text-sm text-muted-foreground">Sin preguntas todavía.</p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function QuotationsCard({ organizationId, eventId, event }) {
  const [quotations, setQuotations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [opening, setOpening] = useState(false);

  async function loadQuotations() {
    try {
      setQuotations(await listQuotations(organizationId, eventId));
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudieron cargar las cotizaciones');
    }
  }

  useEffect(() => {
    setLoading(true);
    loadQuotations().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [organizationId, eventId]);

  async function onOpenBids() {
    setOpening(true);
    try {
      await openBids(organizationId, eventId);
      toast.success('Ofertas abiertas');
      await loadQuotations();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudieron abrir las ofertas');
    } finally {
      setOpening(false);
    }
  }

  // El sellado lo hace RLS en la base (services/quotations.py: "no hay
  // lógica de sellado acá, la hace la base") — mientras no se abran las
  // ofertas, el backend no devuelve montos. event.bid_opened_at es la señal
  // real (expuesta en SourcingEventOut); no hace falta inferirlo de si hay
  // filas con total_amount_base.
  const isSealedAndUnopened = event.bid_mode === 'SEALED' && !event.bid_opened_at;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Receipt className="size-4 text-primary" />
          Cotizaciones recibidas
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {loading ? (
          <div className="h-16 animate-pulse rounded-lg bg-secondary" />
        ) : isSealedAndUnopened ? (
          <div className="space-y-3 rounded-lg border border-dashed px-4 py-6 text-center text-sm text-muted-foreground">
            <p className="flex items-center justify-center gap-1.5">
              <Lock className="size-4" />
              Las ofertas están selladas hasta la apertura.
            </p>
            <Button size="sm" onClick={onOpenBids} disabled={opening} className="gap-1.5">
              <Unlock className="size-4" />
              {opening ? 'Abriendo…' : 'Abrir ofertas'}
            </Button>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-lg border">
            <table className="w-full min-w-[640px] text-sm">
              <thead className="border-b bg-secondary/50 text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="px-3 py-2 text-left">Proveedor</th>
                  <th className="px-3 py-2 text-left">Ronda</th>
                  <th className="px-3 py-2 text-left">Total</th>
                  <th className="px-3 py-2 text-left">Moneda</th>
                  <th className="px-3 py-2 text-left">Total (moneda base)</th>
                  <th className="px-3 py-2 text-left">Enviado</th>
                </tr>
              </thead>
              <tbody>
                {quotations.map((q) => (
                  <tr key={q.id} className="border-b last:border-b-0">
                    <td className="px-3 py-2 font-mono text-xs">{q.supplier_organization_id}</td>
                    <td className="px-3 py-2">{q.round_number ?? '—'}</td>
                    <td className="px-3 py-2">{q.total_amount ?? '—'}</td>
                    <td className="px-3 py-2">{q.currency_code ?? '—'}</td>
                    <td className="px-3 py-2">{q.total_amount_base ?? '—'}</td>
                    <td className="px-3 py-2">{formatDateTime(q.submitted_at)}</td>
                  </tr>
                ))}
                {quotations.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-3 py-4 text-center text-muted-foreground">
                      Aún no hay cotizaciones enviadas.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
