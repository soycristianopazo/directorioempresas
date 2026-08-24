import { z } from 'zod'

export const updateProfileSchema = z.object({
  firstName: z.string().trim().min(2, 'Ingresa tu nombre').max(80),
  lastName: z.string().trim().min(2, 'Ingresa tu apellido').max(80),
  jobTitle: z.string().trim().max(120).optional().or(z.literal('')),
  phone: z.string().trim().max(32).optional().or(z.literal('')),
  locale: z.enum(['es-CL', 'es', 'en']),
})

export type UpdateProfileValues = z.input<typeof updateProfileSchema>
export type UpdateProfileInput = z.output<typeof updateProfileSchema>
