import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useParams } from 'react-router-dom';
import { toast } from 'sonner';
import {
  Ban,
  ClipboardCheck,
  FileSearch,
  HelpCircle,
  Lock,
  Plus,
  Receipt,
  Send,
  Trash2,
  Unlock,
  UserPlus,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { SelectNative } from '@/components/ui/select-native';
import { Textarea } from '@/components/ui/textarea';
import { CategorySelector } from '@/components/CategorySelector';
import { ConversationPanel } from '@/components/ConversationPanel';
import { getCertificationTypes } from '@/lib/credentialsApi';
import { listPrograms } from '@/lib/accreditationApi';
import { getIndustries } from '@/lib/taxonomyApi';
import { getAdminDivisions } from '@/lib/referenceApi';
import { addCriterion, addItem, deleteCriterion, getEvent, publishEvent } from '@/lib/sourcingApi';
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
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [invitations, setInvitations] = useState([]);

  async function loadAll() {
    const d = await getEvent(activeOrg.id, eventId);
    setDetail(d);
    if (d.event.status === 'PUBLISHED') {
      setInvitations(await listInvitations(activeOrg.id, eventId));
    } else {
      setInvitations([]);
    }
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
    setQuestions(await listQuestions(organizationId, eventId));
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
    setQuotations(await listQuotations(organizationId, eventId));
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
