'use server'

import { revalidatePath } from 'next/cache'
import { createClient } from '@/lib/supabase/server'
import { requireUser } from '@/server/policies/authorize'
import { updateProfileSchema } from '@/server/schemas/profile'
import { run } from './run'
import type { ActionResult } from './types'

export async function updateProfileAction(raw: unknown): Promise<ActionResult> {
  return run(async () => {
    const input = updateProfileSchema.parse(raw)
    const ctx = await requireUser()

    const supabase = await createClient()
    const emptyToNull = (value: string | undefined) => (value?.trim() ? value.trim() : null)

    // La policy profiles_update_own limita el UPDATE a la propia fila; el
    // .eq() es la segunda vuelta de la misma restricción.
    const { error } = await supabase
      .from('profiles')
      .update({
        first_name: input.firstName,
        last_name: input.lastName,
        job_title: emptyToNull(input.jobTitle),
        phone: emptyToNull(input.phone),
        locale: input.locale,
      })
      .eq('id', ctx.userId)

    if (error) throw error

    revalidatePath('/perfil')
    revalidatePath('/', 'layout')
    return undefined
  })
}
