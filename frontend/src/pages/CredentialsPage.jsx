import { useEffect, useRef, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { Award, BriefcaseBusiness, Image as ImageIcon, Plus, Trash2, Upload, Users } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { SelectNative } from '@/components/ui/select-native';
import { Textarea } from '@/components/ui/textarea';
import { CategorySelector } from '@/components/CategorySelector';
import { getIndustries } from '@/lib/taxonomyApi';
import {
  getCertificationTypes,
  listCertifications,
  createCertification,
  deleteCertification,
  listClientReferences,
  createClientReference,
  deleteClientReference,
  listCaseStudies,
  createCaseStudy,
  deleteCaseStudy,
  setCaseStudyTaxonomy,
  listCaseStudyMedia,
  uploadCaseStudyMedia,
  deleteCaseStudyMedia,
} from '@/lib/credentialsApi';

function flatten(nodes, depth = 0, acc = []) {
  for (const node of nodes) {
    acc.push({ ...node, depth });
    if (node.children?.length) flatten(node.children, depth + 1, acc);
  }
  return acc;
}

const certSchema = z.object({
  certificationTypeId: z.string().min(1, 'Selecciona un tipo'),
  certificateNumber: z.string().trim().optional(),
  issuedBy: z.string().trim().optional(),
  issuedAt: z.string().optional(),
  validUntil: z.string().optional(),
});

const refSchema = z.object({
  clientName: z.string().trim().min(2, 'Ingresa el nombre del cliente'),
  industryId: z.string().optional(),
  since: z.string().optional(),
  isPublic: z.boolean().default(false),
});

const caseSchema = z.object({
  name: z.string().trim().min(2, 'Ingresa un título'),
  clientReferenceId: z.string().optional(),
  startedOn: z.string().optional(),
  endedOn: z.string().optional(),
  description: z.string().trim().max(5000).optional(),
  results: z.string().trim().max(2000).optional(),
  isPublic: z.boolean().default(false),
});

export default function CredentialsPage() {
  const { activeOrg } = useAuth();
  const [certTypes, setCertTypes] = useState([]);
  const [certifications, setCertifications] = useState([]);
  const [references, setReferences] = useState([]);
  const [caseStudies, setCaseStudies] = useState([]);
  const [industries, setIndustries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedCase, setExpandedCase] = useState(null);

  async function loadAll() {
    try {
      const [types, certs, refs, cases, inds] = await Promise.all([
        getCertificationTypes(),
        listCertifications(activeOrg.id),
        listClientReferences(activeOrg.id),
        listCaseStudies(activeOrg.id),
        getIndustries(),
      ]);
      setCertTypes(types);
      setCertifications(certs);
      setReferences(refs);
      setCaseStudies(cases);
      setIndustries(flatten(inds));
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudieron cargar las credenciales');
    }
  }

  useEffect(() => {
    if (!activeOrg) return;
    setLoading(true);
    loadAll().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id]);

  const certForm = useForm({
    resolver: zodResolver(certSchema),
    defaultValues: { certificationTypeId: '', certificateNumber: '', issuedBy: '', issuedAt: '', validUntil: '' },
  });
  const refForm = useForm({
    resolver: zodResolver(refSchema),
    defaultValues: { clientName: '', industryId: '', since: '', isPublic: false },
  });
  const caseForm = useForm({
    resolver: zodResolver(caseSchema),
    defaultValues: { name: '', clientReferenceId: '', startedOn: '', endedOn: '', description: '', results: '', isPublic: false },
  });

  async function onCreateCert(values) {
    try {
      await createCertification(activeOrg.id, {
        certification_type_id: values.certificationTypeId,
        certificate_number: values.certificateNumber || null,
        scope: null,
        issued_by: values.issuedBy || null,
        issued_at: values.issuedAt || null,
        valid_until: values.validUntil || null,
      });
      toast.success('Certificación agregada');
      certForm.reset({ certificationTypeId: '', certificateNumber: '', issuedBy: '', issuedAt: '', validUntil: '' });
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo agregar');
    }
  }

  async function onDeleteCert(id) {
    try {
      await deleteCertification(activeOrg.id, id);
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo eliminar');
    }
  }

  async function onCreateRef(values) {
    try {
      await createClientReference(activeOrg.id, {
        client_organization_id: null,
        client_name: values.clientName,
        industry_id: values.industryId || null,
        since: values.since || null,
        is_public: values.isPublic,
      });
      toast.success('Referencia agregada');
      refForm.reset({ clientName: '', industryId: '', since: '', isPublic: false });
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo agregar');
    }
  }

  async function onDeleteRef(id) {
    try {
      await deleteClientReference(activeOrg.id, id);
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo eliminar');
    }
  }

  async function onCreateCase(values) {
    try {
      await createCaseStudy(activeOrg.id, {
        name: values.name,
        client_reference_id: values.clientReferenceId || null,
        industry_id: null,
        admin_division_id: null,
        started_on: values.startedOn || null,
        ended_on: values.endedOn || null,
        duration_months: null,
        description: values.description || null,
        results: values.results || null,
        reference_contact_id: null,
        is_public: values.isPublic,
      });
      toast.success('Caso de éxito agregado');
      caseForm.reset({ name: '', clientReferenceId: '', startedOn: '', endedOn: '', description: '', results: '', isPublic: false });
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo agregar');
    }
  }

  async function onDeleteCase(id) {
    try {
      await deleteCaseStudy(activeOrg.id, id);
      if (expandedCase === id) setExpandedCase(null);
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo eliminar');
    }
  }

  if (!activeOrg) return null;

  return (
    <div className="space-y-8">
      <Helmet>
        <title>Certificaciones y casos de éxito · Directorio de Empresas</title>
      </Helmet>

      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Certificaciones y casos de éxito</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Credenciales autodeclaradas — la verificación documental completa llega en una fase posterior.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Award className="size-4 text-primary" />
            Certificaciones ({certifications.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {loading ? (
            <div className="h-16 animate-pulse rounded-lg bg-secondary" />
          ) : (
            <ul className="space-y-2">
              {certifications.map((c) => {
                const type = certTypes.find((t) => t.id === c.certification_type_id);
                return (
                  <li key={c.id} className="flex items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm">
                    <div>
                      <span className="font-medium">{type?.name ?? c.certification_type_id}</span>
                      {c.certificate_number && <span className="ml-2 text-xs text-muted-foreground">N° {c.certificate_number}</span>}
                      {c.valid_until && <span className="ml-2 text-xs text-muted-foreground">vence {c.valid_until}</span>}
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => onDeleteCert(c.id)}>
                      <Trash2 className="size-3.5" />
                    </Button>
                  </li>
                );
              })}
              {certifications.length === 0 && <p className="text-sm text-muted-foreground">Sin certificaciones registradas.</p>}
            </ul>
          )}

          <form onSubmit={certForm.handleSubmit(onCreateCert)} className="grid gap-3 border-t pt-4 sm:grid-cols-2" noValidate>
            <div className="space-y-1.5">
              <Label htmlFor="cert-type">Tipo de certificación</Label>
              <SelectNative id="cert-type" {...certForm.register('certificationTypeId')}>
                <option value="">Selecciona…</option>
                {certTypes.map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </SelectNative>
              {certForm.formState.errors.certificationTypeId && (
                <p className="text-xs text-destructive">{certForm.formState.errors.certificationTypeId.message}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="cert-number">N° de certificado</Label>
              <Input id="cert-number" {...certForm.register('certificateNumber')} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="cert-issued-by">Emitido por</Label>
              <Input id="cert-issued-by" {...certForm.register('issuedBy')} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="cert-issued-at">Fecha de emisión</Label>
              <Input id="cert-issued-at" type="date" {...certForm.register('issuedAt')} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="cert-valid-until">Válido hasta</Label>
              <Input id="cert-valid-until" type="date" {...certForm.register('validUntil')} />
            </div>
            <div className="flex items-end sm:col-span-2">
              <Button type="submit" disabled={certForm.formState.isSubmitting} className="gap-1.5">
                <Plus className="size-4" />
                Agregar certificación
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="size-4 text-primary" />
            Referencias de clientes ({references.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {loading ? (
            <div className="h-16 animate-pulse rounded-lg bg-secondary" />
          ) : (
            <ul className="space-y-2">
              {references.map((r) => (
                <li key={r.id} className="flex items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm">
                  <div>
                    <span className="font-medium">{r.client_name}</span>
                    {r.since && <span className="ml-2 text-xs text-muted-foreground">desde {r.since}</span>}
                    {r.is_public && <Badge variant="neutral" className="ml-2 text-[10px]">público</Badge>}
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => onDeleteRef(r.id)}>
                    <Trash2 className="size-3.5" />
                  </Button>
                </li>
              ))}
              {references.length === 0 && <p className="text-sm text-muted-foreground">Sin referencias registradas.</p>}
            </ul>
          )}

          <form onSubmit={refForm.handleSubmit(onCreateRef)} className="grid gap-3 border-t pt-4 sm:grid-cols-2" noValidate>
            <div className="space-y-1.5">
              <Label htmlFor="ref-client-name">Cliente</Label>
              <Input id="ref-client-name" {...refForm.register('clientName')} />
              {refForm.formState.errors.clientName && (
                <p className="text-xs text-destructive">{refForm.formState.errors.clientName.message}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ref-industry">Industria</Label>
              <SelectNative id="ref-industry" {...refForm.register('industryId')}>
                <option value="">Sin especificar</option>
                {industries.map((i) => (
                  <option key={i.id} value={i.id}>{'—'.repeat(i.depth)} {i.name}</option>
                ))}
              </SelectNative>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ref-since">Cliente desde</Label>
              <Input id="ref-since" type="date" {...refForm.register('since')} />
            </div>
            <label className="flex items-center gap-2 self-end text-sm">
              <input type="checkbox" className="size-4" {...refForm.register('isPublic')} />
              Visible en el perfil público
            </label>
            <div className="sm:col-span-2">
              <Button type="submit" disabled={refForm.formState.isSubmitting} className="gap-1.5">
                <Plus className="size-4" />
                Agregar referencia
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BriefcaseBusiness className="size-4 text-primary" />
            Casos de éxito ({caseStudies.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {loading ? (
            <div className="h-16 animate-pulse rounded-lg bg-secondary" />
          ) : (
            <ul className="space-y-2">
              {caseStudies.map((cs) => (
                <li key={cs.id} className="rounded-lg border px-3 py-2 text-sm">
                  <div className="flex items-center justify-between gap-2">
                    <button
                      className="flex-1 text-left font-medium hover:underline"
                      onClick={() => setExpandedCase(expandedCase === cs.id ? null : cs.id)}
                    >
                      {cs.name}
                      {cs.is_public && <Badge variant="neutral" className="ml-2 text-[10px]">público</Badge>}
                    </button>
                    <Button variant="ghost" size="sm" onClick={() => onDeleteCase(cs.id)}>
                      <Trash2 className="size-3.5" />
                    </Button>
                  </div>
                  {expandedCase === cs.id && <CaseStudyDetail organizationId={activeOrg.id} caseStudyId={cs.id} />}
                </li>
              ))}
              {caseStudies.length === 0 && <p className="text-sm text-muted-foreground">Sin casos de éxito registrados.</p>}
            </ul>
          )}

          <form onSubmit={caseForm.handleSubmit(onCreateCase)} className="grid gap-3 border-t pt-4 sm:grid-cols-2" noValidate>
            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="case-name">Título</Label>
              <Input id="case-name" {...caseForm.register('name')} />
              {caseForm.formState.errors.name && (
                <p className="text-xs text-destructive">{caseForm.formState.errors.name.message}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="case-client-ref">Referencia de cliente</Label>
              <SelectNative id="case-client-ref" {...caseForm.register('clientReferenceId')}>
                <option value="">Sin especificar</option>
                {references.map((r) => (
                  <option key={r.id} value={r.id}>{r.client_name}</option>
                ))}
              </SelectNative>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="case-started">Inicio</Label>
              <Input id="case-started" type="date" {...caseForm.register('startedOn')} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="case-ended">Término</Label>
              <Input id="case-ended" type="date" {...caseForm.register('endedOn')} />
            </div>
            <label className="flex items-center gap-2 self-end text-sm">
              <input type="checkbox" className="size-4" {...caseForm.register('isPublic')} />
              Visible en el perfil público
            </label>
            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="case-description">Descripción</Label>
              <Textarea id="case-description" maxLength={5000} {...caseForm.register('description')} />
            </div>
            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="case-results">Resultados</Label>
              <Textarea id="case-results" maxLength={2000} {...caseForm.register('results')} />
            </div>
            <div className="sm:col-span-2">
              <Button type="submit" disabled={caseForm.formState.isSubmitting} className="gap-1.5">
                <Plus className="size-4" />
                Agregar caso de éxito
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

function CaseStudyDetail({ organizationId, caseStudyId }) {
  const [nodeIds, setNodeIds] = useState([]);
  const [media, setMedia] = useState([]);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  async function load() {
    try {
      const mediaList = await listCaseStudyMedia(organizationId, caseStudyId);
      setMedia(mediaList);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo cargar el material del caso');
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseStudyId]);

  async function onSaveTaxonomy(selected) {
    const ids = selected.map((s) => s.node_id);
    setNodeIds(selected);
    try {
      await setCaseStudyTaxonomy(organizationId, caseStudyId, ids);
      toast.success('Categorías actualizadas');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo guardar');
    }
  }

  async function handleUpload(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await uploadCaseStudyMedia(organizationId, caseStudyId, { file });
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo subir la foto');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }

  async function handleDelete(mediaId) {
    try {
      await deleteCaseStudyMedia(organizationId, caseStudyId, mediaId);
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo eliminar');
    }
  }

  return (
    <div className="mt-3 space-y-3 border-t pt-3">
      <div>
        <p className="mb-1.5 text-xs font-medium text-muted-foreground">Categorías relacionadas</p>
        <CategorySelector selected={nodeIds} onChange={onSaveTaxonomy} allowPrimary={false} />
      </div>
      <div>
        <p className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
          <ImageIcon className="size-3.5" />
          Fotos
        </p>
        <div className="flex flex-wrap gap-2">
          {media.map((m) => (
            <div key={m.id} className="group relative">
              <img src={m.url} alt={m.caption ?? ''} className="size-16 rounded-lg border object-cover" />
              <button
                onClick={() => handleDelete(m.id)}
                className="absolute -right-1.5 -top-1.5 hidden size-5 items-center justify-center rounded-full border bg-background group-hover:flex"
                aria-label="Eliminar"
              >
                <Trash2 className="size-2.5" />
              </button>
            </div>
          ))}
        </div>
        <Input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          onChange={handleUpload}
          disabled={uploading}
          className="mt-2 max-w-xs"
        />
      </div>
      <p className="flex items-center gap-1 text-[10px] text-muted-foreground">
        <Upload className="size-3" />
        Los cambios de categorías y fotos se guardan al instante.
      </p>
    </div>
  );
}
