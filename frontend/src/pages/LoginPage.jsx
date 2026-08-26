import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { BadgeCheck, FileSearch, Gavel, ShieldCheck } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useI18n } from '@/context/I18nContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import logo from '@/assets/logo.png';

const schema = z.object({
  email: z.string().trim().toLowerCase().email('Correo inválido'),
  password: z.string().min(1, 'Ingresa tu contraseña'),
});

const FEATURES = [
  { icon: ShieldCheck, label: 'Acreditación verificada de proveedores' },
  { icon: FileSearch, label: 'Sourcing y cotizaciones en un solo flujo' },
  { icon: Gavel, label: 'Evaluación y adjudicación con trazabilidad' },
  { icon: BadgeCheck, label: 'Vendor list y gestión de contratos' },
];

export default function LoginPage() {
  const { login } = useAuth();
  const { t } = useI18n();
  const navigate = useNavigate();
  const location = useLocation();
  const [formError, setFormError] = useState(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(schema), defaultValues: { email: '', password: '' } });

  async function onSubmit(values) {
    setFormError(null);
    try {
      await login(values.email, values.password);
      navigate(location.state?.from || '/dashboard', { replace: true });
    } catch {
      // Mensaje deliberadamente genérico: no revelar si el correo existe.
      setFormError(t('auth.invalidCredentials'));
    }
  }

  return (
    <div className="flex min-h-dvh">
      <Helmet>
        <title>Iniciar sesión · Directorio de Empresas</title>
      </Helmet>

      <div className="relative hidden w-1/2 flex-col justify-between overflow-hidden bg-brand-teal-dark px-12 py-12 text-white lg:flex">
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.06]"
          style={{ backgroundImage: 'radial-gradient(currentColor 1px, transparent 1px)', backgroundSize: '22px 22px' }}
        />
        <div className="pointer-events-none absolute -right-24 -top-24 size-96 rounded-full bg-brand-teal/30 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-32 -left-16 size-96 rounded-full bg-brand-lime/10 blur-3xl" />

        <Link to="/" className="relative flex items-center gap-2">
          <img src={logo} alt="Directorio de Empresas" className="h-14 w-auto brightness-0 invert" />
        </Link>

        <div className="relative max-w-md space-y-6">
          <p className="text-3xl font-semibold leading-tight tracking-tight">
            El directorio B2B que conecta proveedores y compradores
          </p>
          <p className="text-white/70">
            Acredita tu empresa, publica lo que ofreces o necesitas, y lleva cada cotización de la
            conversación a la adjudicación — con trazabilidad completa.
          </p>

          <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {FEATURES.map((feature) => (
              <li key={feature.label} className="flex items-start gap-2.5 text-sm text-white/80">
                <feature.icon className="mt-0.5 size-4 shrink-0 text-brand-lime" />
                <span>{feature.label}</span>
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-xs text-white/40">Plataforma B2B de proveedores y compradores en Chile</p>
      </div>

      <main className="flex w-full flex-1 flex-col lg:w-1/2">
        <div className="flex flex-1 flex-col items-center justify-center px-6 py-12">
          <Link to="/" className="mb-8 lg:hidden">
            <img src={logo} alt="Directorio de Empresas" className="h-8 w-auto" />
          </Link>

          <div className="w-full max-w-sm space-y-6">
            <div className="space-y-1">
              <h1 className="text-2xl font-semibold tracking-tight">Iniciar sesión</h1>
              <p className="text-sm text-muted-foreground">Accede a tu cuenta para continuar.</p>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
              <div className="space-y-1.5">
                <Label htmlFor="email">{t('auth.email')}</Label>
                <Input id="email" type="email" autoComplete="email" aria-invalid={Boolean(errors.email)} {...register('email')} />
                {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="password">{t('auth.password')}</Label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  aria-invalid={Boolean(errors.password)}
                  {...register('password')}
                />
                {errors.password && <p className="text-xs text-destructive">{errors.password.message}</p>}
              </div>

              {formError && <p className="text-sm text-destructive">{formError}</p>}

              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? 'Ingresando…' : 'Ingresar'}
              </Button>
            </form>

            <p className="text-sm text-muted-foreground">
              ¿No tienes cuenta?{' '}
              <Link to="/register" className="font-medium text-primary hover:underline">
                Crear cuenta
              </Link>
            </p>
          </div>
        </div>

        <p className="pb-6 text-center text-xs text-muted-foreground">
          © Dosoft {new Date().getFullYear()}. Todos los derechos reservados.
        </p>
      </main>
    </div>
  );
}
