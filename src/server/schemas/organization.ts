import { z } from 'zod'

/**
 * Esquemas Zod compartidos entre React Hook Form y las Server Actions.
 *
 * La misma definición valida en el navegador (UX) y en el servidor
 * (seguridad). El cliente nunca es la autoridad: aquí se revalida siempre.
 */

/** Valida un RUT chileno por módulo 11. Refleja app.is_valid_rut() en SQL. */
export function isValidRut(rut: string): boolean {
  const clean = rut.replace(/[^0-9kK]/g, '').toUpperCase()
  if (clean.length < 2 || clean.length > 9) return false

  const body = clean.slice(0, -1)
  const dv = clean.slice(-1)
  if (!/^\d+$/.test(body)) return false

  let sum = 0
  let multiplier = 2
  for (let i = body.length - 1; i >= 0; i -= 1) {
    sum += Number(body[i]) * multiplier
    multiplier = multiplier === 7 ? 2 : multiplier + 1
  }

  const rest = 11 - (sum % 11)
  const expected = rest === 11 ? '0' : rest === 10 ? 'K' : String(rest)

  return dv === expected
}

export function formatRut(rut: string): string {
  const clean = rut.replace(/[^0-9kK]/g, '').toUpperCase()
  if (clean.length < 2) return clean
  return `${clean.slice(0, -1)}-${clean.slice(-1)}`
}

const rutSchema = z
  .string()
  .trim()
  .min(1, 'El RUT es obligatorio')
  .refine(isValidRut, 'El RUT no es válido')
  .transform(formatRut)

export const organizationCapabilitySchema = z.enum(['BUYER', 'SUPPLIER'])

export const createOrganizationSchema = z.object({
  legalName: z
    .string()
    .trim()
    .min(2, 'La razón social debe tener al menos 2 caracteres')
    .max(200, 'La razón social es demasiado larga'),
  tradeName: z
    .string()
    .trim()
    .max(200, 'El nombre comercial es demasiado largo')
    .optional()
    .or(z.literal('')),
  rut: rutSchema,
  capabilities: z
    .array(organizationCapabilitySchema)
    .min(1, 'Selecciona al menos si compras, vendes o ambas'),
  countryCode: z.string().length(2).default('CL'),
})

/**
 * Los esquemas con `.default()`, `.transform()` o `z.coerce` tienen tipos de
 * entrada y de salida distintos. Se exponen ambos: el formulario trabaja con
 * el de entrada (lo que el usuario escribe) y el servidor con el de salida
 * (lo ya validado y normalizado).
 */
export type CreateOrganizationValues = z.input<typeof createOrganizationSchema>
export type CreateOrganizationInput = z.output<typeof createOrganizationSchema>

export const updateOrganizationSchema = z.object({
  organizationId: z.string().uuid(),
  legalName: z.string().trim().min(2).max(200),
  tradeName: z.string().trim().max(200).optional().or(z.literal('')),
  shortDescription: z
    .string()
    .trim()
    .max(280, 'La descripción corta no puede superar 280 caracteres')
    .optional()
    .or(z.literal('')),
  description: z.string().trim().max(5000).optional().or(z.literal('')),
  valueProposition: z.string().trim().max(1000).optional().or(z.literal('')),
  websiteUrl: z
    .string()
    .trim()
    .url('Debe ser una URL válida, incluyendo https://')
    .optional()
    .or(z.literal('')),
  linkedinUrl: z.string().trim().url('Debe ser una URL válida').optional().or(z.literal('')),
  generalEmail: z.string().trim().email('Correo inválido').optional().or(z.literal('')),
  generalPhone: z.string().trim().max(32).optional().or(z.literal('')),
  foundedYear: z.coerce
    .number()
    .int()
    .min(1800, 'Año demasiado antiguo')
    .max(new Date().getFullYear(), 'El año no puede ser futuro')
    .optional(),
  companySize: z.enum(['MICRO', 'SMALL', 'MEDIUM', 'LARGE', 'ENTERPRISE']).optional(),
  employeeCount: z.coerce.number().int().min(0).max(1_000_000).optional(),
  visibility: z.enum(['PUBLIC', 'REGISTERED', 'BUYERS_ONLY', 'PRIVATE']),
})

export type UpdateOrganizationValues = z.input<typeof updateOrganizationSchema>
export type UpdateOrganizationInput = z.output<typeof updateOrganizationSchema>

export const inviteMemberSchema = z.object({
  organizationId: z.string().uuid(),
  email: z.string().trim().toLowerCase().email('Correo inválido'),
  roleCode: z.string().min(1, 'Selecciona un rol'),
})

export type InviteMemberInput = z.infer<typeof inviteMemberSchema>

export const switchOrganizationSchema = z.object({
  organizationId: z.string().uuid(),
})
