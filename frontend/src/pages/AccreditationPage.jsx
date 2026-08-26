import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { toast } from 'sonner';
import { CheckCircle2, ClipboardList, ShieldCheck } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { SelectNative } from '@/components/ui/select-native';
import {
  enroll,
  getEnrollmentDetail,
  listEnrollments,
  listPrograms,
  renewEnrollment,
  respondToObservation,
  submitEvidence,
  submitForReview,
} from '@/lib/accreditationApi';
import { listDocuments, listDocumentVersions } from '@/lib/documentsApi';
import { listCertifications } from '@/lib/credentialsApi';

const STATUS_LABELS = {
  INCOMPLETE: 'Incompleta',
  PENDING_DOCUMENTS: 'Reuniendo documentos',
  UNDER_REVIEW: 'En revisión',
  ACCREDITED: 'Acreditado',
  OBSERVED: 'Con observaciones',
  SUSPENDED: 'Suspendido',
  REJECTED: 'Rechazado',
  EXPIRED: 'Vencido',
};

const STATUS_VARIANT = {
  ACCREDITED: 'bg-emerald-600 text-white hover:bg-emerald-600',
  REJECTED: 'bg-destructive text-destructive-foreground hover:bg-destructive',
  OBSERVED: 'bg-amber-500 text-white hover:bg-amber-500',
  SUSPENDED: 'bg-destructive text-destructive-foreground hover:bg-destructive',
  EXPIRED: 'bg-destructive text-destructive-foreground hover:bg-destructive',
};

function StatusBadge({ status }) {
  return <Badge className={STATUS_VARIANT[status]}>{STATUS_LABELS[status] || status}</Badge>;
}

export default function AccreditationPage() {
  const { activeOrg } = useAuth();
  const [programs, setPrograms] = useState([]);
  const [enrollments, setEnrollments] = useState([]);
  const [loading, setLoading] = useState(true);

  async function loadAll() {
    try {
      const [progs, enrs] = await Promise.all([listPrograms(), listEnrollments(activeOrg.id)]);
      setPrograms(progs);
      setEnrollments(enrs);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudieron cargar los programas de acreditación');
    }
  }

  useEffect(() => {
    if (!activeOrg) return;
    setLoading(true);
    loadAll().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id]);

  async function onEnroll(programId) {
    try {
      await enroll(activeOrg.id, programId);
      toast.success('Postulación creada');
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo postular');
    }
  }

  if (!activeOrg) return null;

  const enrolledProgramIds = new Set(enrollments.map((e) => e.program_id));
  const availablePrograms = programs.filter((p) => !enrolledProgramIds.has(p.id));

  return (
    <div className="space-y-8">
      <Helmet>
        <title>Acreditación · Directorio de Empresas</title>
      </Helmet>

      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Acreditación</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Postula a un programa de acreditación y sigue el estado de tu revisión.
        </p>
      </header>

      {loading ? (
        <div className="h-32 animate-pulse rounded-lg bg-secondary" />
      ) : (
        <>
          {enrollments.map((enr) => (
            <EnrollmentCard
              key={enr.id}
              enrollmentSummary={enr}
              organizationId={activeOrg.id}
              onChanged={loadAll}
            />
          ))}

          {availablePrograms.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <ShieldCheck className="size-4 text-primary" />
                  Programas disponibles
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {availablePrograms.map((p) => (
                  <div
                    key={p.id}
                    className="flex items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm"
                  >
                    <div>
                      <span className="font-medium">{p.name}</span>
                      {p.description && (
                        <p className="text-xs text-muted-foreground">{p.description}</p>
                      )}
                    </div>
                    <Button size="sm" onClick={() => onEnroll(p.id)}>
                      Postular
                    </Button>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {enrollments.length === 0 && availablePrograms.length === 0 && (
            <p className="text-sm text-muted-foreground">No hay programas de acreditación disponibles.</p>
          )}
        </>
      )}
    </div>
  );
}

function EnrollmentCard({ enrollmentSummary, organizationId, onChanged }) {
  const [detail, setDetail] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [certifications, setCertifications] = useState([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [renewing, setRenewing] = useState(false);

  async function load() {
    try {
      const [d, docs, certs] = await Promise.all([
        getEnrollmentDetail(organizationId, enrollmentSummary.id),
        listDocuments(organizationId),
        listCertifications(organizationId),
      ]);
      setDetail(d);
      setDocuments(docs);
      setCertifications(certs);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo cargar el detalle de la postulación');
    }
  }

  useEffect(() => {
    if (dialogOpen) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dialogOpen]);

  async function onSubmitForReview() {
    try {
      await submitForReview(organizationId, enrollmentSummary.id);
      toast.success('Enviado a revisión');
      await Promise.all([load(), onChanged()]);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo enviar a revisión');
    }
  }

  async function onRespondObservation() {
    try {
      await respondToObservation(organizationId, enrollmentSummary.id);
      toast.success('Puedes editar la evidencia de nuevo');
      await Promise.all([load(), onChanged()]);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo continuar');
    }
  }

  async function onRenew() {
    setRenewing(true);
    try {
      await renewEnrollment(organizationId, enrollmentSummary.id);
      toast.success('Renovación iniciada — completa la información de este año');
      await onChanged();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo iniciar la renovación');
    } finally {
      setRenewing(false);
    }
  }

  const sections = detail?.fulfillments.reduce((acc, f) => {
    (acc[f.group_id] ??= { name: f.group_name, items: [] }).items.push(f);
    return acc;
  }, {});

  const canEdit = ['PENDING_DOCUMENTS', 'OBSERVED'].includes(enrollmentSummary.status);
  const isAccredited = enrollmentSummary.status === 'ACCREDITED';
  const isExpired = enrollmentSummary.status === 'EXPIRED';

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="flex items-center gap-2">
            <ClipboardList className="size-4 text-primary" />
            {enrollmentSummary.program_name}
          </CardTitle>
          <StatusBadge status={enrollmentSummary.status} />
        </div>
        {!isAccredited && <CardDescription>Completitud: {enrollmentSummary.completion_pct}%</CardDescription>}
      </CardHeader>
      <CardContent className="space-y-3">
        {isAccredited && (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 dark:border-emerald-900 dark:bg-emerald-950/20">
            <div className="flex items-center gap-2 text-sm font-medium text-emerald-700 dark:text-emerald-400">
              <CheckCircle2 className="size-4" />
              Acreditado
              {enrollmentSummary.valid_until && (
                <span className="font-normal text-emerald-700/80 dark:text-emerald-400/80">
                  · vigente hasta {new Date(enrollmentSummary.valid_until).toLocaleDateString('es-CL')}
                </span>
              )}
            </div>
            <Button asChild size="sm" variant="outline">
              <Link to={`/empresa/acreditacion/${enrollmentSummary.id}/certificado`}>Ver certificado</Link>
            </Button>
          </div>
        )}

        {isExpired && (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3">
            <p className="text-sm text-muted-foreground">
              Tu acreditación venció — se renueva anualmente. Renueva la información para volver a postular.
            </p>
            <Button size="sm" disabled={renewing} onClick={onRenew}>
              Renovar acreditación
            </Button>
          </div>
        )}

        {!isAccredited && !isExpired && (
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm">
                {['INCOMPLETE', 'PENDING_DOCUMENTS'].includes(enrollmentSummary.status)
                  ? 'Completar acreditación'
                  : 'Ver checklist'}
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>{enrollmentSummary.program_name}</DialogTitle>
              </DialogHeader>

              {detail && (
                <div className="space-y-4">
                  {Object.values(sections || {}).map((section) => (
                    <div key={section.name}>
                      <h3 className="mb-2 text-sm font-medium">{section.name}</h3>
                      <div className="space-y-2">
                        {section.items.map((item) => (
                          <RequirementRow
                            key={item.id}
                            item={item}
                            organizationId={organizationId}
                            enrollmentId={enrollmentSummary.id}
                            documents={documents}
                            certifications={certifications}
                            editable={canEdit}
                            onSaved={load}
                          />
                        ))}
                      </div>
                    </div>
                  ))}

                  {enrollmentSummary.status === 'PENDING_DOCUMENTS' && (
                    <Button onClick={onSubmitForReview}>Enviar a revisión</Button>
                  )}
                  {enrollmentSummary.status === 'OBSERVED' && (
                    <Button onClick={onRespondObservation}>Editar y reenviar</Button>
                  )}

                  {detail.history.length > 0 && (
                    <div className="border-t pt-3">
                      <h3 className="mb-2 text-sm font-medium">Historial</h3>
                      <ul className="space-y-1 text-xs text-muted-foreground">
                        {detail.history.map((h) => (
                          <li key={h.id}>
                            {STATUS_LABELS[h.to_status] || h.to_status}
                            {h.reason && ` — ${h.reason}`}
                            {' · '}
                            {new Date(h.created_at).toLocaleDateString('es-CL')}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </DialogContent>
          </Dialog>
        )}
      </CardContent>
    </Card>
  );
}

const FULFILLMENT_LABELS = {
  PENDING: 'Pendiente',
  SUBMITTED: 'Enviado',
  UNDER_REVIEW: 'En revisión',
  OBSERVED: 'Observado',
  APPROVED: 'Aprobado',
  REJECTED: 'Rechazado',
  EXPIRED: 'Vencido',
};

const FULFILLMENT_VARIANT = {
  APPROVED: 'bg-emerald-600 text-white hover:bg-emerald-600',
  OBSERVED: 'bg-amber-500 text-white hover:bg-amber-500',
  REJECTED: 'bg-destructive text-destructive-foreground hover:bg-destructive',
};

function RequirementRow({ item, organizationId, enrollmentId, documents, certifications, editable, onSaved }) {
  const [selectedValue, setSelectedValue] = useState('');
  const [saving, setSaving] = useState(false);

  const isDocumentKind = item.requirement_kind === 'DOCUMENT';
  const isCertificationKind = item.requirement_kind === 'CERTIFICATION';

  async function onAttach() {
    if (!selectedValue) return;
    setSaving(true);
    try {
      if (isDocumentKind) {
        const doc = documents.find((d) => d.id === selectedValue);
        const versions = await listDocumentVersions(organizationId, selectedValue);
        const activeVersion = versions.find((v) => v.status === 'ACTIVE');
        if (!activeVersion) {
          toast.error(`Sube primero el documento "${doc?.name}" en Documentos`);
          return;
        }
        await submitEvidence(organizationId, enrollmentId, {
          requirementId: item.requirement_id,
          documentVersionId: activeVersion.id,
        });
      } else if (isCertificationKind) {
        await submitEvidence(organizationId, enrollmentId, {
          requirementId: item.requirement_id,
          certificationId: selectedValue,
        });
      }
      toast.success('Evidencia adjuntada');
      await onSaved();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo adjuntar la evidencia');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-lg border px-3 py-2 text-sm">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          {item.status === 'APPROVED' && <CheckCircle2 className="size-3.5 text-emerald-600" />}
          <span className="font-medium">{item.requirement_name}</span>
          {item.is_mandatory && <span className="text-xs text-muted-foreground">(obligatorio)</span>}
        </div>
        <Badge className={FULFILLMENT_VARIANT[item.status]}>
          {FULFILLMENT_LABELS[item.status] || item.status}
        </Badge>
      </div>
      {item.observation && (
        <p className="mt-1 text-xs text-amber-700">Observación: {item.observation}</p>
      )}

      {editable && (isDocumentKind || isCertificationKind) && (
        <div className="mt-2 flex items-center gap-2">
          <SelectNative
            value={selectedValue}
            onChange={(e) => setSelectedValue(e.target.value)}
            className="max-w-xs"
          >
            <option value="">Selecciona…</option>
            {isDocumentKind &&
              documents.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            {isCertificationKind &&
              certifications.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.certification_type_id}
                </option>
              ))}
          </SelectNative>
          <Button size="sm" variant="outline" disabled={!selectedValue || saving} onClick={onAttach}>
            Adjuntar
          </Button>
        </div>
      )}
    </div>
  );
}
