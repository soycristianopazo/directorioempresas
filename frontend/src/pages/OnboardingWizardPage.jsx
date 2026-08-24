import { useEffect, useRef, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { useNavigate, useParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { ArrowRight, Check } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { SelectNative } from '@/components/ui/select-native';
import { ProfileCompletion } from '@/components/ProfileCompletion';
import { IndustrySelector } from '@/components/IndustrySelector';
import { CategorySelector } from '@/components/CategorySelector';
import { AdminDivisionSelector } from '@/components/AdminDivisionSelector';
import { cn } from '@/lib/utils';
import {
  getLocations,
  createLocation,
  getContacts,
  createContact,
  getMedia,
  uploadMedia,
  getOrganizationIndustries,
  setOrganizationIndustry,
  removeOrganizationIndustry,
  getOrganizationTerritories,
  addOrganizationTerritory,
  removeOrganizationTerritory,
} from '@/lib/organizationProfileApi';
import { listOfferings, createOffering, setOfferingTaxonomyNodes } from '@/lib/offeringsApi';
import { getCertificationTypes, listCertifications, createCertification } from '@/lib/credentialsApi';

/**
 * Continuación del onboarding (paso 1 = OnboardingPage, crea la
 * organización). Pasos 2-8: cada uno persiste de inmediato contra la API
 * real al confirmar — "guardado parcial" no es un borrador local, es que
 * abandonar el wizard a mitad de camino no pierde nada, porque ya está
 * escrito en Postgres. Por eso no existe una tabla de "progreso del
 * wizard": cada paso simplemente lee su propio estado actual (¿ya hay una
 * ubicación? ¿ya hay un logo?) y se comporta de forma idempotente si el
 * usuario vuelve a pasar por acá.
 */

const STEPS = [
  { n: 2, title: 'Ubicación principal' },
  { n: 3, title: 'Contacto principal' },
  { n: 4, title: 'Logo' },
  { n: 5, title: 'Industrias que atiendes' },
  { n: 6, title: 'Cobertura territorial' },
  { n: 7, title: 'Tu primer producto o servicio' },
  { n: 8, title: 'Certificaciones' },
];

export default function OnboardingWizardPage() {
  const { step } = useParams();
  const stepNum = Math.min(8, Math.max(2, Number(step) || 2));
  const navigate = useNavigate();
  const { activeOrg, refresh } = useAuth();

  const meta = STEPS.find((s) => s.n === stepNum) ?? STEPS[0];

  async function goNext() {
    await refresh();
    if (stepNum >= 8) {
      navigate('/dashboard');
      return;
    }
    navigate(`/onboarding/${stepNum + 1}`);
  }

  function goBack() {
    if (stepNum <= 2) return;
    navigate(`/onboarding/${stepNum - 1}`);
  }

  if (!activeOrg) return null;

  return (
    <main className="mx-auto flex min-h-dvh max-w-lg flex-col justify-center px-6 py-12">
      <Helmet>
        <title>{meta.title} · Directorio de Empresas</title>
      </Helmet>

      <div className="mb-8 space-y-2">
        <p className="text-sm font-medium text-primary">Paso {stepNum} de 8</p>
        <h1 className="text-2xl font-semibold tracking-tight">{meta.title}</h1>
        <div className="flex gap-1">
          {STEPS.map((s) => (
            <div
              key={s.n}
              className={cn('h-1 flex-1 rounded-full', s.n <= stepNum ? 'bg-primary' : 'bg-secondary')}
            />
          ))}
        </div>
      </div>

      {stepNum === 2 && <LocationStep organizationId={activeOrg.id} onDone={goNext} />}
      {stepNum === 3 && <ContactStep organizationId={activeOrg.id} onDone={goNext} />}
      {stepNum === 4 && <LogoStep organizationId={activeOrg.id} onDone={goNext} />}
      {stepNum === 5 && <IndustriesStep organizationId={activeOrg.id} onDone={goNext} />}
      {stepNum === 6 && <TerritoriesStep organizationId={activeOrg.id} onDone={goNext} />}
      {stepNum === 7 && <FirstOfferingStep organizationId={activeOrg.id} onDone={goNext} />}
      {stepNum === 8 && (
        <CertificationsStep
          organizationId={activeOrg.id}
          completionPct={activeOrg.completion_pct}
          onFinish={goNext}
        />
      )}

      <div className="mt-6 flex items-center justify-between text-sm">
        <button
          type="button"
          onClick={goBack}
          disabled={stepNum <= 2}
          className="text-muted-foreground hover:text-foreground disabled:opacity-0"
        >
          Atrás
        </button>
        {stepNum < 8 && (
          <button type="button" onClick={goNext} className="text-muted-foreground hover:text-foreground">
            Omitir por ahora
          </button>
        )}
      </div>
    </main>
  );
}

function LocationStep({ organizationId, onDone }) {
  const [existing, setExisting] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getLocations(organizationId)
      .then((locs) => setExisting(locs[0] ?? null))
      .finally(() => setLoading(false));
  }, [organizationId]);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(z.object({ addressLine: z.string().trim().min(3, 'Ingresa la dirección') })),
    defaultValues: { addressLine: '' },
  });

  async function onSubmit(values) {
    try {
      await createLocation(organizationId, {
        location_type: 'HEADQUARTERS',
        address_line: values.addressLine,
        is_headquarters: true,
      });
      toast.success('Ubicación guardada');
      onDone();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo guardar');
    }
  }

  if (loading) return <div className="h-24 animate-pulse rounded-lg bg-secondary" />;

  if (existing) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Ya tienes una ubicación registrada: <span className="font-medium text-foreground">{existing.address_line}</span>
        </p>
        <Button onClick={onDone} size="lg" className="w-full gap-1.5">
          Continuar
          <ArrowRight className="size-4" />
        </Button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      <p className="text-sm text-muted-foreground">¿Dónde está la casa matriz o la base principal de tu empresa?</p>
      <div className="space-y-1.5">
        <Label htmlFor="wizard-address">Dirección</Label>
        <Input id="wizard-address" placeholder="Av. Principal 123, Antofagasta" {...register('addressLine')} />
        {errors.addressLine && <p className="text-xs text-destructive">{errors.addressLine.message}</p>}
      </div>
      <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? 'Guardando…' : 'Guardar y continuar'}
      </Button>
    </form>
  );
}

function ContactStep({ organizationId, onDone }) {
  const [existing, setExisting] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getContacts(organizationId)
      .then((contacts) => setExisting(contacts[0] ?? null))
      .finally(() => setLoading(false));
  }, [organizationId]);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(
      z
        .object({
          fullName: z.string().trim().min(2, 'Ingresa el nombre'),
          email: z.string().trim().email('Correo inválido').optional().or(z.literal('')),
          phone: z.string().trim().optional(),
        })
        .refine((data) => data.email || data.phone, { message: 'Ingresa al menos un correo o teléfono', path: ['email'] }),
    ),
    defaultValues: { fullName: '', email: '', phone: '' },
  });

  async function onSubmit(values) {
    try {
      await createContact(organizationId, {
        full_name: values.fullName,
        job_title: null,
        contact_type: 'COMERCIAL',
        email: values.email || null,
        phone: values.phone || null,
        whatsapp: null,
        linkedin_url: null,
        is_public: true,
        is_primary: true,
      });
      toast.success('Contacto guardado');
      onDone();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo guardar');
    }
  }

  if (loading) return <div className="h-24 animate-pulse rounded-lg bg-secondary" />;

  if (existing) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Ya tienes un contacto registrado: <span className="font-medium text-foreground">{existing.full_name}</span>
        </p>
        <Button onClick={onDone} size="lg" className="w-full gap-1.5">
          Continuar
          <ArrowRight className="size-4" />
        </Button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      <p className="text-sm text-muted-foreground">¿Quién responde cuando un comprador quiere contactarte?</p>
      <div className="space-y-1.5">
        <Label htmlFor="wizard-contact-name">Nombre</Label>
        <Input id="wizard-contact-name" {...register('fullName')} />
        {errors.fullName && <p className="text-xs text-destructive">{errors.fullName.message}</p>}
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="wizard-contact-email">Correo</Label>
        <Input id="wizard-contact-email" type="email" {...register('email')} />
        {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="wizard-contact-phone">Teléfono</Label>
        <Input id="wizard-contact-phone" {...register('phone')} />
      </div>
      <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? 'Guardando…' : 'Guardar y continuar'}
      </Button>
    </form>
  );
}

function LogoStep({ organizationId, onDone }) {
  const [logo, setLogo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    getMedia(organizationId)
      .then((media) => setLogo(media.find((m) => m.media_type === 'LOGO') ?? null))
      .finally(() => setLoading(false));
  }, [organizationId]);

  async function handleUpload(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await uploadMedia(organizationId, { mediaType: 'LOGO', file });
      toast.success('Logo subido');
      onDone();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo subir el logo');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }

  if (loading) return <div className="h-24 animate-pulse rounded-lg bg-secondary" />;

  if (logo) {
    return (
      <div className="space-y-4 text-center">
        <img src={logo.url} alt="Logo" className="mx-auto size-20 rounded-lg border object-contain p-1" />
        <Button onClick={onDone} size="lg" className="w-full gap-1.5">
          Continuar
          <ArrowRight className="size-4" />
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Un logo hace que tu perfil se vea profesional. Puedes agregarlo después si no lo tienes a mano.
      </p>
      <Input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/gif"
        onChange={handleUpload}
        disabled={uploading}
      />
    </div>
  );
}

function IndustriesStep({ organizationId, onDone }) {
  const [industries, setIndustries] = useState([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    setIndustries(await getOrganizationIndustries(organizationId));
  }

  useEffect(() => {
    load().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [organizationId]);

  const selectedIds = industries.map((i) => i.industry_id);

  async function handleChange(newIds) {
    const added = newIds.filter((id) => !selectedIds.includes(id));
    const removed = selectedIds.filter((id) => !newIds.includes(id));
    try {
      for (const id of added) {
        await setOrganizationIndustry(organizationId, { industry_id: id, years_experience: null, is_primary: false });
      }
      for (const id of removed) {
        await removeOrganizationIndustry(organizationId, id);
      }
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo actualizar');
    }
  }

  if (loading) return <div className="h-24 animate-pulse rounded-lg bg-secondary" />;

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">¿A qué industrias les vendes o quieres venderles?</p>
      <IndustrySelector selectedIds={selectedIds} onChange={handleChange} />
      <Button onClick={onDone} size="lg" className="w-full gap-1.5" disabled={selectedIds.length === 0}>
        Continuar
        <ArrowRight className="size-4" />
      </Button>
    </div>
  );
}

function TerritoriesStep({ organizationId, onDone }) {
  const [territories, setTerritories] = useState([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    setTerritories(await getOrganizationTerritories(organizationId));
  }

  useEffect(() => {
    load().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [organizationId]);

  async function handleAdd(divisionId) {
    try {
      await addOrganizationTerritory(organizationId, divisionId);
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo agregar');
    }
  }

  async function handleRemove(territoryId) {
    try {
      await removeOrganizationTerritory(organizationId, territoryId);
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo eliminar');
    }
  }

  if (loading) return <div className="h-24 animate-pulse rounded-lg bg-secondary" />;

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">¿Dónde puede operar tu empresa?</p>
      <div className="flex flex-wrap gap-2">
        {territories.map((t) => (
          <span key={t.id} className="flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs">
            {t.name}
            <button onClick={() => handleRemove(t.id)} aria-label="Quitar" className="text-muted-foreground hover:text-foreground">
              ×
            </button>
          </span>
        ))}
        {territories.length === 0 && <p className="text-sm text-muted-foreground">Todavía no hay cobertura declarada.</p>}
      </div>
      <AdminDivisionSelector onAdd={handleAdd} />
      <Button onClick={onDone} size="lg" className="w-full gap-1.5" disabled={territories.length === 0}>
        Continuar
        <ArrowRight className="size-4" />
      </Button>
    </div>
  );
}

function FirstOfferingStep({ organizationId, onDone }) {
  const [offerings, setOfferings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [createdId, setCreatedId] = useState(null);
  const [selectedNodes, setSelectedNodes] = useState([]);

  useEffect(() => {
    listOfferings(organizationId)
      .then(setOfferings)
      .finally(() => setLoading(false));
  }, [organizationId]);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(
      z.object({
        name: z.string().trim().min(2, 'Mínimo 2 caracteres'),
        shortDescription: z.string().trim().min(1, 'Describe brevemente qué ofreces').max(280),
      }),
    ),
    defaultValues: { name: '', shortDescription: '' },
  });

  async function onSubmit(values) {
    try {
      const id = await createOffering(organizationId, {
        offering_type: 'SERVICE',
        name: values.name,
        short_description: values.shortDescription,
      });
      setCreatedId(id);
      toast.success('Producto o servicio creado');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo crear');
    }
  }

  async function onSaveCategory(nodes) {
    setSelectedNodes(nodes);
    if (!createdId) return;
    try {
      await setOfferingTaxonomyNodes(organizationId, createdId, nodes);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo guardar la categoría');
    }
  }

  if (loading) return <div className="h-24 animate-pulse rounded-lg bg-secondary" />;

  if (offerings.length > 0 && !createdId) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Ya tienes {offerings.length} {offerings.length === 1 ? 'producto o servicio' : 'productos o servicios'} en tu catálogo.
        </p>
        <Button onClick={onDone} size="lg" className="w-full gap-1.5">
          Continuar
          <ArrowRight className="size-4" />
        </Button>
      </div>
    );
  }

  if (createdId) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Ahora clasifícalo — así los compradores lo encuentran. Precio, fotos y detalles se agregan después desde el catálogo.
        </p>
        <CategorySelector selected={selectedNodes} onChange={onSaveCategory} />
        <Button onClick={onDone} size="lg" className="w-full gap-1.5" disabled={selectedNodes.length === 0}>
          Continuar
          <ArrowRight className="size-4" />
        </Button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      <p className="text-sm text-muted-foreground">¿Qué es lo primero que ofreces? Puedes agregar más después.</p>
      <div className="space-y-1.5">
        <Label htmlFor="wizard-offering-name">Nombre</Label>
        <Input id="wizard-offering-name" placeholder="Traslado de trabajadores a faena" {...register('name')} />
        {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="wizard-offering-desc">Descripción corta</Label>
        <Input id="wizard-offering-desc" maxLength={280} {...register('shortDescription')} />
        {errors.shortDescription && <p className="text-xs text-destructive">{errors.shortDescription.message}</p>}
      </div>
      <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? 'Creando…' : 'Crear y continuar'}
      </Button>
    </form>
  );
}

function CertificationsStep({ organizationId, completionPct, onFinish }) {
  const [certTypes, setCertTypes] = useState([]);
  const [certifications, setCertifications] = useState([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    const [types, certs] = await Promise.all([getCertificationTypes(), listCertifications(organizationId)]);
    setCertTypes(types);
    setCertifications(certs);
  }

  useEffect(() => {
    load().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [organizationId]);

  const {
    register,
    handleSubmit,
    reset,
    formState: { isSubmitting },
  } = useForm({
    resolver: zodResolver(z.object({ certificationTypeId: z.string().min(1, 'Selecciona un tipo') })),
    defaultValues: { certificationTypeId: '' },
  });

  async function onSubmit(values) {
    try {
      await createCertification(organizationId, {
        certification_type_id: values.certificationTypeId,
        certificate_number: null,
        scope: null,
        issued_by: null,
        issued_at: null,
        valid_until: null,
      });
      toast.success('Certificación agregada');
      reset({ certificationTypeId: '' });
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo agregar');
    }
  }

  if (loading) return <div className="h-24 animate-pulse rounded-lg bg-secondary" />;

  return (
    <div className="space-y-5">
      <p className="text-sm text-muted-foreground">¿Tienes alguna certificación vigente? Es opcional, pero ayuda a que te elijan.</p>

      {certifications.length > 0 && (
        <ul className="space-y-1.5 text-sm">
          {certifications.map((c) => {
            const type = certTypes.find((t) => t.id === c.certification_type_id);
            return (
              <li key={c.id} className="flex items-center gap-2">
                <Check className="size-3.5 text-primary" />
                {type?.name ?? c.certification_type_id}
              </li>
            );
          })}
        </ul>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="flex items-end gap-2" noValidate>
        <div className="flex-1 space-y-1.5">
          <Label htmlFor="wizard-cert-type">Tipo de certificación</Label>
          <SelectNative id="wizard-cert-type" {...register('certificationTypeId')}>
            <option value="">Selecciona…</option>
            {certTypes.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </SelectNative>
        </div>
        <Button type="submit" disabled={isSubmitting}>
          Agregar
        </Button>
      </form>

      <div className="space-y-3 rounded-lg border p-4">
        <ProfileCompletion pct={completionPct} />
      </div>

      <Button onClick={onFinish} size="lg" className="w-full gap-1.5">
        Ir a mi panel
        <ArrowRight className="size-4" />
      </Button>
    </div>
  );
}
