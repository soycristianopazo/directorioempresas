import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Link, useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

const schema = z
  .object({
    firstName: z.string().trim().min(2, 'Ingresa tu nombre'),
    lastName: z.string().trim().min(2, 'Ingresa tu apellido'),
    email: z.string().trim().toLowerCase().email('Correo inválido'),
    password: z
      .string()
      .min(10, 'Usa al menos 10 caracteres')
      .regex(/[a-z]/, 'Incluye una minúscula')
      .regex(/[A-Z]/, 'Incluye una mayúscula')
      .regex(/[0-9]/, 'Incluye un número'),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Las contraseñas no coinciden',
    path: ['confirmPassword'],
  });

export default function RegisterPage() {
  const { register: registerAccount } = useAuth();
  const navigate = useNavigate();
  const [formError, setFormError] = useState(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: { firstName: '', lastName: '', email: '', password: '', confirmPassword: '' },
  });

  async function onSubmit(values) {
    setFormError(null);
    try {
      await registerAccount(values);
      navigate('/dashboard', { replace: true });
    } catch (error) {
      setFormError(error.response?.data?.detail || 'No se pudo crear la cuenta');
    }
  }

  return (
    <main className="flex min-h-dvh flex-col items-center justify-center px-6 py-12">
      <Helmet>
        <title>Crear cuenta · Directorio de Empresas</title>
      </Helmet>

      <Link to="/" className="mb-8 font-semibold tracking-tight">
        Directorio de Empresas
      </Link>

      <div className="w-full max-w-sm space-y-6">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Crear cuenta</h1>
          <p className="text-sm text-muted-foreground">
            Primero tu cuenta personal. Después registras tu empresa.
          </p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="firstName">Nombre</Label>
              <Input id="firstName" autoComplete="given-name" {...register('firstName')} />
              {errors.firstName && <p className="text-xs text-destructive">{errors.firstName.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="lastName">Apellido</Label>
              <Input id="lastName" autoComplete="family-name" {...register('lastName')} />
              {errors.lastName && <p className="text-xs text-destructive">{errors.lastName.message}</p>}
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="email">Correo corporativo</Label>
            <Input id="email" type="email" autoComplete="email" {...register('email')} />
            {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="password">Contraseña</Label>
            <Input id="password" type="password" autoComplete="new-password" {...register('password')} />
            {errors.password && <p className="text-xs text-destructive">{errors.password.message}</p>}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="confirmPassword">Repetir contraseña</Label>
            <Input id="confirmPassword" type="password" autoComplete="new-password" {...register('confirmPassword')} />
            {errors.confirmPassword && (
              <p className="text-xs text-destructive">{errors.confirmPassword.message}</p>
            )}
          </div>

          {formError && <p className="text-sm text-destructive">{formError}</p>}

          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? 'Creando cuenta…' : 'Crear cuenta'}
          </Button>
        </form>

        <p className="text-sm text-muted-foreground">
          ¿Ya tienes cuenta?{' '}
          <Link to="/login" className="font-medium text-primary hover:underline">
            Iniciar sesión
          </Link>
        </p>
      </div>
    </main>
  );
}
