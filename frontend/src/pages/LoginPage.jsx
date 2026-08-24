import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { useAuth } from '@/context/AuthContext';
import { useI18n } from '@/context/I18nContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

const schema = z.object({
  email: z.string().trim().toLowerCase().email('Correo inválido'),
  password: z.string().min(1, 'Ingresa tu contraseña'),
});

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
    <main className="flex min-h-dvh flex-col items-center justify-center px-6 py-12">
      <Helmet>
        <title>Iniciar sesión · Directorio de Empresas</title>
      </Helmet>

      <Link to="/" className="mb-8 font-semibold tracking-tight">
        Directorio de Empresas
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
    </main>
  );
}
