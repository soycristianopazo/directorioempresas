'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { createOrganizationSchema, formatRut } from '@/server/schemas/organization'
import { createOrganizationAction } from '@/server/actions/organization'
import { Button } from '@/components/ui/button'
import { Field, Input } from '@/components/ui/field'
import { cn } from '@/lib/utils'
import type {
  CreateOrganizationInput,
  CreateOrganizationValues,
} from '@/server/schemas/organization'

const CAPABILITIES = [
  {
    value: 'SUPPLIER' as const,
    title: 'Vendemos',
    description: 'Ofrecemos productos o servicios y queremos que nos encuentren.',
  },
  {
    value: 'BUYER' as const,
    title: 'Compramos',
    description: 'Buscamos proveedores y gestionamos cotizaciones.',
  },
]

export function CreateOrganizationForm() {
  const router = useRouter()
  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    setValue,
    control,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<CreateOrganizationValues, unknown, CreateOrganizationInput>({
    resolver: zodResolver(createOrganizationSchema),
    defaultValues: {
      legalName: '',
      tradeName: '',
      rut: '',
      capabilities: ['SUPPLIER'],
      countryCode: 'CL',
    },
  })

  // useWatch en vez de watch(): watch() devuelve una función no memoizable y
  // el React Compiler descarta la optimización del componente completo.
  const capabilities = useWatch({ control, name: 'capabilities' }) ?? []

  function toggleCapability(value: 'BUYER' | 'SUPPLIER') {
    const current = new Set(capabilities)
    if (current.has(value)) {
      current.delete(value)
    } else {
      current.add(value)
    }
    setValue('capabilities', [...current] as CreateOrganizationValues['capabilities'], {
      shouldValidate: true,
    })
  }

  async function onSubmit(values: CreateOrganizationInput) {
    setFormError(null)

    const result = await createOrganizationAction(values)

    if (!result.ok) {
      if (result.fieldErrors) {
        for (const [field, messages] of Object.entries(result.fieldErrors)) {
          if (messages?.[0]) {
            setError(field as keyof CreateOrganizationValues, { message: messages[0] })
          }
        }
      }
      setFormError(result.error ?? 'No se pudo crear la organización')
      return
    }

    router.replace('/dashboard')
    router.refresh()
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
      <Field
        label="Razón social"
        htmlFor="legalName"
        hint="Tal como aparece en el SII."
        error={errors.legalName?.message}
        required
      >
        <Input id="legalName" autoComplete="organization" {...register('legalName')} />
      </Field>

      <Field
        label="Nombre comercial"
        htmlFor="tradeName"
        hint="Con el que te conocen tus clientes. Define la URL de tu perfil."
        error={errors.tradeName?.message}
      >
        <Input id="tradeName" {...register('tradeName')} />
      </Field>

      <Field
        label="RUT"
        htmlFor="rut"
        hint="Se valida con dígito verificador."
        error={errors.rut?.message}
        required
      >
        <Input
          id="rut"
          inputMode="text"
          placeholder="76.086.428-5"
          {...register('rut', {
            onBlur: (e) => {
              const value = (e.target as HTMLInputElement).value
              if (value) setValue('rut', formatRut(value), { shouldValidate: true })
            },
          })}
        />
      </Field>

      <fieldset className="space-y-2">
        <legend className="text-ink-700 text-sm font-medium">¿Qué hace tu empresa aquí?</legend>
        <p className="text-ink-500 text-xs">
          Puedes marcar ambas. Muchas empresas compran y venden a la vez.
        </p>
        <div className="grid gap-2 sm:grid-cols-2">
          {CAPABILITIES.map((option) => {
            const checked = capabilities.includes(option.value)
            return (
              <button
                key={option.value}
                type="button"
                onClick={() => toggleCapability(option.value)}
                aria-pressed={checked}
                className={cn(
                  'rounded-lg border p-3 text-left transition-colors',
                  checked
                    ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/30'
                    : 'border-ink-300 hover:bg-ink-50 dark:hover:bg-ink-900',
                )}
              >
                <span className="block text-sm font-medium">{option.title}</span>
                <span className="text-ink-500 mt-0.5 block text-xs">{option.description}</span>
              </button>
            )
          })}
        </div>
        {errors.capabilities && (
          <p role="alert" className="text-xs text-[var(--color-danger)]">
            {errors.capabilities.message}
          </p>
        )}
      </fieldset>

      {formError && (
        <p role="alert" className="text-sm text-[var(--color-danger)]">
          {formError}
        </p>
      )}

      <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? 'Creando…' : 'Crear organización'}
      </Button>
    </form>
  )
}
