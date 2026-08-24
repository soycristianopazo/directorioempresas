import { useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { toast } from 'sonner';
import { useAuth } from '@/context/AuthContext';
import { createOrganization } from '@/lib/organizationsApi';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';

/** Espejo de app.is_valid_rut() — validación en cliente, la base la repite. */
function isValidRut(rut) {
  const clean = rut.replace(/[^0-9kK]/g, '').toUpperCase();
  if (clean.length < 2 || clean.length > 9) return false;
  const body = clean.slice(0, -1);
  const dv = clean.slice(-1);
  if (!/^\d+$/.test(body)) return false;
  let sum = 0;
  let mult = 2;
  for (let i = body.length - 1; i >= 0; i -= 1) {
    sum += Number(body[i]) * mult;
    mult = mult === 7 ? 2 : mult + 1;
  }
  const rest = 11 - (sum % 11);
  const expected = rest === 11 ? '0' : rest === 10 ? 'K' : String(rest);
  return dv === expected;
}

function formatRut(rut) {
  const clean = rut.replace(/[^0-9kK]/g, '').toUpperCase();
  if (clean.length < 2) return clean;
  return `${clean.slice(0, -1)}-${clean.slice(-1)}`;
}

const schema = z.object({
  legalName: z.string().trim().min(2, 'La razón social debe tener al menos 2 caracteres'),
  tradeName: z.string().trim().optional().or(z.literal('')),
  rut: z.string().trim().min(1, 'El RUT es obligatorio').refine(isValidRut, 'El RUT no es válido'),
  capabilities: z.array(z.enum(['BUYER', 'SUPPLIER'])).min(1, 'Selecciona al menos si compras, vendes o ambas'),
});

const CAPABILITIES = [
  { value: 'SUPPLIER', title: 'Vendemos', description: 'Ofrecemos productos o servicios y queremos que nos encuentren.' },
  { value: 'BUYER', title: 'Compramos', description: 'Buscamos proveedores y gestionamos cotizaciones.' },
];

export default function OnboardingPage() {
  const { refresh, switchOrganization, memberships } = useAuth();
  const navigate = useNavigate();
  const [formError, setFormError] = useState(null);

  const {
    register,
    handleSubmit,
    setValue,
    control,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: { legalName: '', tradeName: '', rut: '', capabilities: ['SUPPLIER'] },
  });

  const capabilities = useWatch({ control, name: 'capabilities' }) ?? [];

  function toggleCapability(value) {
    const current = new Set(capabilities);
    current.has(value) ? current.delete(value) : current.add(value);
    setValue('capabilities', [...current], { shouldValidate: true });
  }

  async function onSubmit(values) {
    setFormError(null);
    try {
      const organizationId = await createOrganization({
        legal_name: values.legalName,
        trade_name: values.tradeName || null,
        rut: formatRut(values.rut),
        capabilities: values.capabilities,
        country_code: 'CL',
      });
      await refresh();
      await switchOrganization(organizationId);
      navigate('/onboarding/2', { replace: true });
    } catch (error) {
      setFormError(error.response?.data?.detail || 'No se pudo crear la organización');
      toast.error('No se pudo crear la organización');
    }
  }

  return (
    <main className="mx-auto flex min-h-dvh max-w-lg flex-col justify-center px-6 py-12">
      <Helmet>
        <title>Registra tu empresa · Directorio de Empresas</title>
      </Helmet>

      <div className="mb-8 space-y-1">
        <p className="text-sm font-medium text-primary">
          {memberships.length > 0 ? 'Nueva organización' : 'Paso 1 de 8'}
        </p>
        <h1 className="text-2xl font-semibold tracking-tight">Registra tu empresa</h1>
        <p className="text-sm text-muted-foreground">
          Con estos datos creamos tu organización. Después completarás industrias, catálogo,
          cobertura y acreditación.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
        <div className="space-y-1.5">
          <Label htmlFor="legalName">Razón social</Label>
          <Input id="legalName" autoComplete="organization" {...register('legalName')} />
          {errors.legalName && <p className="text-xs text-destructive">{errors.legalName.message}</p>}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="tradeName">Nombre comercial</Label>
          <Input id="tradeName" {...register('tradeName')} />
          <p className="text-xs text-muted-foreground">Con el que te conocen tus clientes. Define la URL de tu perfil.</p>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="rut">RUT</Label>
          <Input
            id="rut"
            placeholder="76.086.428-5"
            {...register('rut', {
              onBlur: (e) => {
                if (e.target.value) setValue('rut', formatRut(e.target.value), { shouldValidate: true });
              },
            })}
          />
          <p className="text-xs text-muted-foreground">Se valida con dígito verificador.</p>
          {errors.rut && <p className="text-xs text-destructive">{errors.rut.message}</p>}
        </div>

        <fieldset className="space-y-2">
          <legend className="text-sm font-medium">¿Qué hace tu empresa aquí?</legend>
          <p className="text-xs text-muted-foreground">Puedes marcar ambas. Muchas empresas compran y venden a la vez.</p>
          <div className="grid gap-2 sm:grid-cols-2">
            {CAPABILITIES.map((option) => {
              const checked = capabilities.includes(option.value);
              return (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => toggleCapability(option.value)}
                  aria-pressed={checked}
                  className={cn(
                    'rounded-lg border p-3 text-left transition-colors',
                    checked ? 'border-primary bg-primary/5' : 'hover:bg-accent',
                  )}
                >
                  <span className="block text-sm font-medium">{option.title}</span>
                  <span className="mt-0.5 block text-xs text-muted-foreground">{option.description}</span>
                </button>
              );
            })}
          </div>
          {errors.capabilities && <p className="text-xs text-destructive">{errors.capabilities.message}</p>}
        </fieldset>

        {formError && <p className="text-sm text-destructive">{formError}</p>}

        <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
          {isSubmitting ? 'Creando…' : 'Crear organización'}
        </Button>
      </form>
    </main>
  );
}
