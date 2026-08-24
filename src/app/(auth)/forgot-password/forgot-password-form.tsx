'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { createClient } from '@/lib/supabase/client'
import { publicEnv } from '@/lib/env'
import { Button } from '@/components/ui/button'
import { Field, Input } from '@/components/ui/field'

const schema = z.object({
  email: z.string().trim().toLowerCase().email('Correo inválido'),
})

type FormValues = z.infer<typeof schema>

export function ForgotPasswordForm() {
  const [sent, setSent] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { email: '' } })

  async function onSubmit(values: FormValues) {
    const supabase = createClient()
    await supabase.auth.resetPasswordForEmail(values.email, {
      redirectTo: `${publicEnv.NEXT_PUBLIC_SITE_URL}/auth/callback?next=/reset-password`,
    })

    // Se confirma siempre, haya o no cuenta con ese correo: de lo contrario
    // el formulario se convierte en un oráculo de qué correos están
    // registrados en la plataforma.
    setSent(true)
  }

  if (sent) {
    return (
      <p
        role="status"
        className="border-ink-200 bg-ink-50 dark:border-ink-800 dark:bg-ink-900 rounded-lg border p-4 text-sm"
      >
        Si existe una cuenta con ese correo, recibirás un enlace en los próximos minutos.
      </p>
    )
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      <Field label="Correo" htmlFor="email" error={errors.email?.message} required>
        <Input id="email" type="email" autoComplete="email" {...register('email')} />
      </Field>

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? 'Enviando…' : 'Enviar enlace'}
      </Button>
    </form>
  )
}
