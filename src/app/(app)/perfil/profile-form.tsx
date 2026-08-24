'use client'

import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import {
  updateProfileSchema,
  type UpdateProfileInput,
  type UpdateProfileValues,
} from '@/server/schemas/profile'
import { updateProfileAction } from '@/server/actions/profile'
import { Button } from '@/components/ui/button'
import { Field, Input, Select } from '@/components/ui/field'
import type { Tables } from '@/lib/supabase/database.types'

const LOCALES = [
  { value: 'es-CL', label: 'Español (Chile)' },
  { value: 'es', label: 'Español' },
  { value: 'en', label: 'English' },
] as const

export function ProfileForm({ profile }: { profile: Tables<'profiles'> }) {
  const router = useRouter()

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<UpdateProfileValues, unknown, UpdateProfileInput>({
    resolver: zodResolver(updateProfileSchema),
    defaultValues: {
      firstName: profile.first_name ?? '',
      lastName: profile.last_name ?? '',
      jobTitle: profile.job_title ?? '',
      phone: profile.phone ?? '',
      locale: (['es-CL', 'es', 'en'] as const).includes(
        profile.locale as (typeof LOCALES)[number]['value'],
      )
        ? (profile.locale as (typeof LOCALES)[number]['value'])
        : 'es-CL',
    },
  })

  async function onSubmit(values: UpdateProfileInput) {
    const result = await updateProfileAction(values)

    if (!result.ok) {
      if (result.fieldErrors) {
        for (const [field, messages] of Object.entries(result.fieldErrors)) {
          if (messages?.[0]) {
            setError(field as keyof UpdateProfileValues, { message: messages[0] })
          }
        }
      }
      toast.error(result.error ?? 'No se pudo guardar')
      return
    }

    toast.success('Perfil actualizado')
    router.refresh()
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Nombre" htmlFor="firstName" error={errors.firstName?.message} required>
          <Input id="firstName" autoComplete="given-name" {...register('firstName')} />
        </Field>
        <Field label="Apellido" htmlFor="lastName" error={errors.lastName?.message} required>
          <Input id="lastName" autoComplete="family-name" {...register('lastName')} />
        </Field>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Cargo" htmlFor="jobTitle" error={errors.jobTitle?.message}>
          <Input id="jobTitle" placeholder="Jefe de Abastecimiento" {...register('jobTitle')} />
        </Field>
        <Field label="Teléfono" htmlFor="phone" error={errors.phone?.message}>
          <Input id="phone" type="tel" autoComplete="tel" {...register('phone')} />
        </Field>
      </div>

      <Field label="Idioma" htmlFor="locale" error={errors.locale?.message} required>
        <Select id="locale" {...register('locale')}>
          {LOCALES.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </Select>
      </Field>

      <Button type="submit" disabled={isSubmitting || !isDirty}>
        {isSubmitting ? 'Guardando…' : 'Guardar cambios'}
      </Button>
    </form>
  )
}
