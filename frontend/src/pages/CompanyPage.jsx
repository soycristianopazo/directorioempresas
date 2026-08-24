import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { useAuth } from '@/context/AuthContext';
import { getOrganization, publishOrganization, updateOrganization } from '@/lib/organizationsApi';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { SelectNative } from '@/components/ui/select-native';
import { Textarea } from '@/components/ui/textarea';

const VISIBILITY_OPTIONS = [
  { value: 'PRIVATE', label: 'Privado — solo mi equipo' },
  { value: 'REGISTERED', label: 'Usuarios registrados' },
  { value: 'BUYERS_ONLY', label: 'Solo compradores' },
  { value: 'PUBLIC', label: 'Público — indexable en buscadores' },
];

const SIZE_OPTIONS = [
  { value: '', label: 'Sin especificar' },
  { value: 'MICRO', label: 'Micro (1-9)' },
  { value: 'SMALL', label: 'Pequeña (10-49)' },
  { value: 'MEDIUM', label: 'Mediana (50-199)' },
  { value: 'LARGE', label: 'Grande (200-999)' },
  { value: 'ENTERPRISE', label: 'Corporación (1000+)' },
];

const schema = z.object({
  legalName: z.string().trim().min(2).max(200),
  tradeName: z.string().trim().max(200).optional().or(z.literal('')),
  shortDescription: z.string().trim().max(280).optional().or(z.literal('')),
  description: z.string().trim().max(5000).optional().or(z.literal('')),
  valueProposition: z.string().trim().max(1000).optional().or(z.literal('')),
  websiteUrl: z.string().trim().url('URL inválida').optional().or(z.literal('')),
  linkedinUrl: z.string().trim().url('URL inválida').optional().or(z.literal('')),
  generalEmail: z.string().trim().email('Correo inválido').optional().or(z.literal('')),
  generalPhone: z.string().trim().max(32).optional().or(z.literal('')),
  foundedYear: z.coerce.number().int().min(1800).max(new Date().getFullYear()).optional().or(z.nan()),
  companySize: z.string().optional(),
  employeeCount: z.coerce.number().int().min(0).optional().or(z.nan()),
  visibility: z.enum(['PUBLIC', 'REGISTERED', 'BUYERS_ONLY', 'PRIVATE']),
});

export default function CompanyPage() {
  const { activeOrg, refresh } = useAuth();
  const [org, setOrg] = useState(null);
  const [loading, setLoading] = useState(true);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm({ resolver: zodResolver(schema) });

  useEffect(() => {
    if (!activeOrg) return;
    let cancelled = false;

    getOrganization(activeOrg.id)
      .then((data) => {
        if (cancelled) return;
        setOrg(data);
        reset({
          legalName: data.legal_name,
          tradeName: data.trade_name ?? '',
          shortDescription: data.short_description ?? '',
          description: data.description ?? '',
          valueProposition: data.value_proposition ?? '',
          websiteUrl: data.website_url ?? '',
          linkedinUrl: data.linkedin_url ?? '',
          generalEmail: data.general_email ?? '',
          generalPhone: data.general_phone ?? '',
          foundedYear: data.founded_year ?? undefined,
          companySize: data.company_size ?? '',
          employeeCount: data.employee_count ?? undefined,
          visibility: data.visibility,
        });
      })
      .finally(() => !cancelled && setLoading(false));

    return () => {
      cancelled = true;
    };
  }, [activeOrg, reset]);

  async function onSubmit(values) {
    try {
      await updateOrganization(activeOrg.id, {
        legal_name: values.legalName,
        trade_name: values.tradeName || null,
        short_description: values.shortDescription || null,
        description: values.description || null,
        value_proposition: values.valueProposition || null,
        website_url: values.websiteUrl || null,
        linkedin_url: values.linkedinUrl || null,
        general_email: values.generalEmail || null,
        general_phone: values.generalPhone || null,
        founded_year: Number.isNaN(values.foundedYear) ? null : values.foundedYear,
        company_size: values.companySize || null,
        employee_count: Number.isNaN(values.employeeCount) ? null : values.employeeCount,
        visibility: values.visibility,
      });
      toast.success('Cambios guardados');
      await refresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo guardar');
    }
  }

  async function handlePublish() {
    try {
      await publishOrganization(activeOrg.id);
      toast.success('Perfil publicado');
      await refresh();
      const data = await getOrganization(activeOrg.id);
      setOrg(data);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo publicar');
    }
  }

  if (loading || !org) {
    return (
      <div className="space-y-4" aria-busy="true">
        <div className="h-8 w-64 animate-pulse rounded-lg bg-secondary" />
        <div className="h-48 animate-pulse rounded-xl bg-secondary/60" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <Helmet>
        <title>Mi empresa · Directorio de Empresas</title>
      </Helmet>

      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Mi empresa</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Estos datos alimentan tu perfil público y los filtros de búsqueda.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Identificación</CardTitle>
          <CardDescription>
            La razón social y el RUT solo puede modificarlos el equipo de la plataforma una vez
            verificada la empresa.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-3">
          <Detail label="Razón social" value={org.legal_name} />
          <Detail label="RUT" value={org.primary_identifier} />
          <Detail label="URL del perfil" value={`/proveedores/${org.slug}`} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Perfil corporativo</CardTitle>
          <CardDescription>
            Escribe pensando en quien compra: qué haces, para quién y qué te diferencia.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Razón social" error={errors.legalName?.message} required>
                <Input {...register('legalName')} />
              </Field>
              <Field label="Nombre comercial" error={errors.tradeName?.message}>
                <Input {...register('tradeName')} />
              </Field>
            </div>

            <Field
              label="Descripción corta"
              hint="Una línea. Es lo que se ve en los resultados de búsqueda."
              error={errors.shortDescription?.message}
            >
              <Input maxLength={280} {...register('shortDescription')} />
            </Field>

            <Field label="Descripción corporativa" error={errors.description?.message}>
              <Textarea rows={5} {...register('description')} />
            </Field>

            <Field
              label="Propuesta de valor"
              hint="Qué te diferencia de otro proveedor de la misma categoría."
              error={errors.valueProposition?.message}
            >
              <Textarea rows={3} {...register('valueProposition')} />
            </Field>

            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Sitio web" error={errors.websiteUrl?.message}>
                <Input type="url" placeholder="https://" {...register('websiteUrl')} />
              </Field>
              <Field label="LinkedIn" error={errors.linkedinUrl?.message}>
                <Input type="url" placeholder="https://" {...register('linkedinUrl')} />
              </Field>
              <Field label="Correo general" error={errors.generalEmail?.message}>
                <Input type="email" {...register('generalEmail')} />
              </Field>
              <Field label="Teléfono" error={errors.generalPhone?.message}>
                <Input type="tel" {...register('generalPhone')} />
              </Field>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <Field label="Año de constitución" error={errors.foundedYear?.message}>
                <Input type="number" min={1800} {...register('foundedYear')} />
              </Field>
              <Field label="Tamaño" error={errors.companySize?.message}>
                <SelectNative {...register('companySize')}>
                  {SIZE_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </SelectNative>
              </Field>
              <Field label="Dotación" error={errors.employeeCount?.message}>
                <Input type="number" min={0} {...register('employeeCount')} />
              </Field>
            </div>

            <Field
              label="Visibilidad del perfil"
              hint="Puedes empezar en privado y publicar cuando el perfil esté listo."
              error={errors.visibility?.message}
              required
            >
              <SelectNative {...register('visibility')}>
                {VISIBILITY_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </SelectNative>
            </Field>

            <Button type="submit" disabled={isSubmitting || !isDirty}>
              {isSubmitting ? 'Guardando…' : 'Guardar cambios'}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <CardTitle>Publicación</CardTitle>
            <Badge variant={org.status === 'ACTIVE' ? 'success' : 'warning'}>
              {org.status === 'ACTIVE' ? 'Publicado' : 'Borrador'}
            </Badge>
          </div>
          <CardDescription>
            Para publicar necesitas nombre comercial, RUT y ambas descripciones. Un perfil
            incompleto genera resultados con ruido y menos contactos.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={handlePublish} disabled={org.status === 'ACTIVE'}>
            {org.status === 'ACTIVE' ? 'Perfil publicado' : 'Publicar perfil'}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

function Detail({ label, value }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-0.5 text-sm font-medium">{value ?? '—'}</dd>
    </div>
  );
}

function Field({ label, hint, error, required, children }) {
  return (
    <div className="space-y-1.5">
      <Label>
        {label}
        {required && <span className="ml-0.5 text-destructive">*</span>}
      </Label>
      {children}
      {hint && !error && <p className="text-xs text-muted-foreground">{hint}</p>}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}
