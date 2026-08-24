'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { createClient } from '@/lib/supabase/client'
import { publicEnv } from '@/lib/env'
import { Button } from '@/components/ui/button'
import { Field, Input } from '@/components/ui/field'

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
  })

type FormValues = z.infer<typeof schema>

export function RegisterForm() {
  const router = useRouter()
  const [formError, setFormError] = useState<string | null>(null)
  const [emailSent, setEmailSent] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { firstName: '', lastName: '', email: '', password: '', confirmPassword: '' },
  })

  async function onSubmit(values: FormValues) {
    setFormError(null)
    const supabase = createClient()

    const { data, error } = await supabase.auth.signUp({
      email: values.email,
      password: values.password,
      options: {
        // El trigger on_auth_user_created copia estos datos al profile.
        data: { first_name: values.firstName, last_name: values.lastName },
        emailRedirectTo: `${publicEnv.NEXT_PUBLIC_SITE_URL}/auth/callback?next=/onboarding`,
      },
    })

    if (error) {
      setFormError(error.message)
      return
    }

    // Con confirmación de correo activada no hay sesión todavía.
    if (data.session) {
      router.replace('/onboarding')
      router.refresh()
    } else {
      setEmailSent(true)
    }
  }

  if (emailSent) {
    return (
      <div
        role="status"
        className="border-ink-200 bg-ink-50 dark:border-ink-800 dark:bg-ink-900 rounded-lg border p-4 text-sm"
      >
        <p className="font-medium">Revisa tu correo</p>
        <p className="text-ink-500 mt-1">
          Te enviamos un enlace para confirmar tu dirección. Al abrirlo continuarás con el registro
          de tu empresa.
        </p>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Nombre" htmlFor="firstName" error={errors.firstName?.message} required>
          <Input id="firstName" autoComplete="given-name" {...register('firstName')} />
        </Field>
        <Field label="Apellido" htmlFor="lastName" error={errors.lastName?.message} required>
          <Input id="lastName" autoComplete="family-name" {...register('lastName')} />
        </Field>
      </div>

      <Field label="Correo corporativo" htmlFor="email" error={errors.email?.message} required>
        <Input id="email" type="email" autoComplete="email" {...register('email')} />
      </Field>

      <Field
        label="Contraseña"
        htmlFor="password"
        hint="Mínimo 10 caracteres, con mayúscula, minúscula y número."
        error={errors.password?.message}
        required
      >
        <Input
          id="password"
          type="password"
          autoComplete="new-password"
          {...register('password')}
        />
      </Field>

      <Field
        label="Repetir contraseña"
        htmlFor="confirmPassword"
        error={errors.confirmPassword?.message}
        required
      >
        <Input
          id="confirmPassword"
          type="password"
          autoComplete="new-password"
          {...register('confirmPassword')}
        />
      </Field>

      {formError && (
        <p role="alert" className="text-sm text-[var(--color-danger)]">
          {formError}
        </p>
      )}

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? 'Creando cuenta…' : 'Crear cuenta'}
      </Button>
    </form>
  )
}
