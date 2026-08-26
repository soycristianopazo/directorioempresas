import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { toast } from 'sonner';
import { ArrowLeft } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { updateProfile, changePassword } from '@/lib/userApi';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

const profileSchema = z.object({
  firstName: z.string().trim().min(2, 'Ingresa tu nombre'),
  lastName: z.string().trim().min(2, 'Ingresa tu apellido'),
});

const passwordSchema = z
  .object({
    currentPassword: z.string().min(1, 'Ingresa tu contraseña actual'),
    newPassword: z
      .string()
      .min(10, 'Usa al menos 10 caracteres')
      .regex(/[a-z]/, 'Incluye una minúscula')
      .regex(/[A-Z]/, 'Incluye una mayúscula')
      .regex(/[0-9]/, 'Incluye un número'),
    confirmPassword: z.string(),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    message: 'Las contraseñas no coinciden',
    path: ['confirmPassword'],
  });

function ProfileForm() {
  const { user, refresh } = useAuth();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm({
    resolver: zodResolver(profileSchema),
    defaultValues: { firstName: '', lastName: '' },
  });

  useEffect(() => {
    if (user) {
      reset({ firstName: user.first_name ?? '', lastName: user.last_name ?? '' });
    }
  }, [user, reset]);

  async function onSubmit(values) {
    try {
      await updateProfile(values);
      await refresh();
      toast.success('Datos actualizados');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo actualizar tu perfil');
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Datos personales</CardTitle>
        <CardDescription>Tu nombre, como aparece en el equipo y en las notificaciones.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <div className="grid gap-4 sm:grid-cols-2">
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
            <Input id="email" value={user?.email ?? ''} disabled />
            <p className="text-xs text-muted-foreground">
              El correo no se puede cambiar desde acá.
            </p>
          </div>

          <Button type="submit" disabled={isSubmitting || !isDirty}>
            {isSubmitting ? 'Guardando…' : 'Guardar cambios'}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function PasswordForm() {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(passwordSchema),
    defaultValues: { currentPassword: '', newPassword: '', confirmPassword: '' },
  });

  async function onSubmit(values) {
    try {
      await changePassword(values);
      reset();
      toast.success('Contraseña actualizada. Se cerraron todas tus sesiones.');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo cambiar la contraseña');
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Contraseña</CardTitle>
        <CardDescription>
          Cambiarla cierra todas tus sesiones activas, incluida esta — vas a tener que
          iniciar sesión de nuevo en los próximos minutos.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <div className="space-y-1.5">
            <Label htmlFor="currentPassword">Contraseña actual</Label>
            <Input
              id="currentPassword"
              type="password"
              autoComplete="current-password"
              {...register('currentPassword')}
            />
            {errors.currentPassword && (
              <p className="text-xs text-destructive">{errors.currentPassword.message}</p>
            )}
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="newPassword">Contraseña nueva</Label>
              <Input
                id="newPassword"
                type="password"
                autoComplete="new-password"
                {...register('newPassword')}
              />
              {errors.newPassword && (
                <p className="text-xs text-destructive">{errors.newPassword.message}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="confirmPassword">Repetir contraseña</Label>
              <Input
                id="confirmPassword"
                type="password"
                autoComplete="new-password"
                {...register('confirmPassword')}
              />
              {errors.confirmPassword && (
                <p className="text-xs text-destructive">{errors.confirmPassword.message}</p>
              )}
            </div>
          </div>

          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Actualizando…' : 'Cambiar contraseña'}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

/** Fuera de AppLayout/AdminLayout a propósito: es la única pantalla que debe
 * verse igual para cualquier usuario autenticado, tenga o no organización
 * activa (comprador, proveedor, platform admin puro) — vivir dentro de
 * cualquiera de los dos layouts la habría atado a ese contexto. */
export default function UserProfilePage() {
  return (
    <main className="mx-auto min-h-dvh max-w-2xl px-6 py-12">
      <Helmet>
        <title>Mi perfil · Directorio de Empresas</title>
      </Helmet>

      <Link
        to="/dashboard"
        className="mb-8 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" />
        Volver
      </Link>

      <h1 className="mb-6 text-2xl font-semibold tracking-tight">Mi perfil</h1>

      <div className="space-y-6">
        <ProfileForm />
        <PasswordForm />
      </div>
    </main>
  );
}
