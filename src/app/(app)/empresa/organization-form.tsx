'use client'

import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import {
  updateOrganizationSchema,
  type UpdateOrganizationInput,
  type UpdateOrganizationValues,
} from '@/server/schemas/organization'
import { updateOrganizationAction } from '@/server/actions/organization'
import { Button } from '@/components/ui/button'
import { Field, Input, Select, Textarea } from '@/components/ui/field'
import type { Tables } from '@/lib/supabase/database.types'

const VISIBILITY_OPTIONS = [
  { value: 'PRIVATE', label: 'Privado — solo mi equipo' },
  { value: 'REGISTERED', label: 'Usuarios registrados' },
  { value: 'BUYERS_ONLY', label: 'Solo compradores' },
  { value: 'PUBLIC', label: 'Público — indexable en buscadores' },
] as const

const SIZE_OPTIONS = [
  { value: '', label: 'Sin especificar' },
  { value: 'MICRO', label: 'Micro (1-9)' },
  { value: 'SMALL', label: 'Pequeña (10-49)' },
  { value: 'MEDIUM', label: 'Mediana (50-199)' },
  { value: 'LARGE', label: 'Grande (200-999)' },
  { value: 'ENTERPRISE', label: 'Corporación (1000+)' },
] as const

export function OrganizationForm({
  organization,
  readOnly,
}: {
  organization: Tables<'organizations'>
  readOnly: boolean
}) {
  const router = useRouter()

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<UpdateOrganizationValues, unknown, UpdateOrganizationInput>({
    resolver: zodResolver(updateOrganizationSchema),
    defaultValues: {
      organizationId: organization.id,
      legalName: organization.legal_name,
      tradeName: organization.trade_name ?? '',
      shortDescription: organization.short_description ?? '',
      description: organization.description ?? '',
      valueProposition: organization.value_proposition ?? '',
      websiteUrl: organization.website_url ?? '',
      linkedinUrl: organization.linkedin_url ?? '',
      generalEmail: organization.general_email ?? '',
      generalPhone: organization.general_phone ?? '',
      foundedYear: organization.founded_year ?? undefined,
      companySize: organization.company_size ?? undefined,
      employeeCount: organization.employee_count ?? undefined,
      visibility: organization.visibility === 'INVITED_ONLY' ? 'PRIVATE' : organization.visibility,
    },
  })

  async function onSubmit(values: UpdateOrganizationInput) {
    const result = await updateOrganizationAction(values)

    if (!result.ok) {
      if (result.fieldErrors) {
        for (const [field, messages] of Object.entries(result.fieldErrors)) {
          if (messages?.[0]) {
            setError(field as keyof UpdateOrganizationValues, { message: messages[0] })
          }
        }
      }
      toast.error(result.error ?? 'No se pudo guardar')
      return
    }

    toast.success('Cambios guardados')
    router.refresh()
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
      <input type="hidden" {...register('organizationId')} />

      <fieldset disabled={readOnly} className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field
            label="Razón social"
            htmlFor="legalName"
            error={errors.legalName?.message}
            required
          >
            <Input id="legalName" {...register('legalName')} />
          </Field>
          <Field label="Nombre comercial" htmlFor="tradeName" error={errors.tradeName?.message}>
            <Input id="tradeName" {...register('tradeName')} />
          </Field>
        </div>

        <Field
          label="Descripción corta"
          htmlFor="shortDescription"
          hint="Una línea. Es lo que se ve en los resultados de búsqueda."
          error={errors.shortDescription?.message}
        >
          <Input
            id="shortDescription"
            maxLength={280}
            placeholder="Transporte de personal para faenas mineras en la Región de Antofagasta."
            {...register('shortDescription')}
          />
        </Field>

        <Field
          label="Descripción corporativa"
          htmlFor="description"
          error={errors.description?.message}
        >
          <Textarea id="description" rows={5} {...register('description')} />
        </Field>

        <Field
          label="Propuesta de valor"
          htmlFor="valueProposition"
          hint="Qué te diferencia de otro proveedor de la misma categoría."
          error={errors.valueProposition?.message}
        >
          <Textarea id="valueProposition" rows={3} {...register('valueProposition')} />
        </Field>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Sitio web" htmlFor="websiteUrl" error={errors.websiteUrl?.message}>
            <Input id="websiteUrl" type="url" placeholder="https://" {...register('websiteUrl')} />
          </Field>
          <Field label="LinkedIn" htmlFor="linkedinUrl" error={errors.linkedinUrl?.message}>
            <Input
              id="linkedinUrl"
              type="url"
              placeholder="https://"
              {...register('linkedinUrl')}
            />
          </Field>
          <Field label="Correo general" htmlFor="generalEmail" error={errors.generalEmail?.message}>
            <Input id="generalEmail" type="email" {...register('generalEmail')} />
          </Field>
          <Field label="Teléfono" htmlFor="generalPhone" error={errors.generalPhone?.message}>
            <Input id="generalPhone" type="tel" {...register('generalPhone')} />
          </Field>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <Field
            label="Año de constitución"
            htmlFor="foundedYear"
            error={errors.foundedYear?.message}
          >
            <Input id="foundedYear" type="number" min={1800} {...register('foundedYear')} />
          </Field>
          <Field label="Tamaño" htmlFor="companySize" error={errors.companySize?.message}>
            <Select id="companySize" {...register('companySize')}>
              {SIZE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Dotación" htmlFor="employeeCount" error={errors.employeeCount?.message}>
            <Input id="employeeCount" type="number" min={0} {...register('employeeCount')} />
          </Field>
        </div>

        <Field
          label="Visibilidad del perfil"
          htmlFor="visibility"
          hint="Puedes empezar en privado y publicar cuando el perfil esté listo."
          error={errors.visibility?.message}
          required
        >
          <Select id="visibility" {...register('visibility')}>
            {VISIBILITY_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
        </Field>
      </fieldset>

      {!readOnly && (
        <Button type="submit" disabled={isSubmitting || !isDirty}>
          {isSubmitting ? 'Guardando…' : 'Guardar cambios'}
        </Button>
      )}

      {readOnly && (
        <p className="text-ink-500 text-sm">
          No tienes permiso para editar el perfil de la organización.
        </p>
      )}
    </form>
  )
}
