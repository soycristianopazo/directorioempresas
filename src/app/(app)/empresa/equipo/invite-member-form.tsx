'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { inviteMemberSchema, type InviteMemberInput } from '@/server/schemas/organization'
import { inviteMemberAction } from '@/server/actions/team'
import { Button } from '@/components/ui/button'
import { Field, Input, Select } from '@/components/ui/field'

export function InviteMemberForm({
  organizationId,
  roles,
}: {
  organizationId: string
  roles: { code: string; name: string }[]
}) {
  const router = useRouter()
  const [acceptUrl, setAcceptUrl] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<InviteMemberInput>({
    resolver: zodResolver(inviteMemberSchema),
    defaultValues: { organizationId, email: '', roleCode: roles[0]?.code ?? '' },
  })

  async function onSubmit(values: InviteMemberInput) {
    const result = await inviteMemberAction(values)

    if (!result.ok) {
      toast.error(result.error ?? 'No se pudo crear la invitación')
      return
    }

    setAcceptUrl(result.data?.acceptUrl ?? null)
    toast.success('Invitación creada')
    reset({ organizationId, email: '', roleCode: values.roleCode })
    router.refresh()
  }

  return (
    <div className="space-y-4">
      <form
        onSubmit={handleSubmit(onSubmit)}
        className="grid gap-3 sm:grid-cols-[1fr_200px_auto]"
        noValidate
      >
        <input type="hidden" {...register('organizationId')} />

        <Field label="Correo" htmlFor="invite-email" error={errors.email?.message} required>
          <Input
            id="invite-email"
            type="email"
            placeholder="persona@empresa.cl"
            {...register('email')}
          />
        </Field>

        <Field label="Rol" htmlFor="invite-role" error={errors.roleCode?.message} required>
          <Select id="invite-role" {...register('roleCode')}>
            {roles.map((role) => (
              <option key={role.code} value={role.code}>
                {role.name}
              </option>
            ))}
          </Select>
        </Field>

        <div className="flex items-end">
          <Button type="submit" disabled={isSubmitting} className="w-full sm:w-auto">
            {isSubmitting ? 'Creando…' : 'Invitar'}
          </Button>
        </div>
      </form>

      {acceptUrl && (
        <div className="border-ink-200 bg-ink-50 dark:border-ink-800 dark:bg-ink-900 rounded-lg border p-3 text-sm">
          <p className="font-medium">Enlace de invitación</p>
          <p className="text-ink-500 mt-1 text-xs">
            El envío automático por correo llega en la fase 5. Por ahora, comparte este enlace:
          </p>
          <code className="dark:bg-ink-950 mt-2 block overflow-x-auto rounded bg-white px-2 py-1.5 text-xs">
            {acceptUrl}
          </code>
        </div>
      )}
    </div>
  )
}
