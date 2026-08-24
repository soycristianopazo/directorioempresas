import 'server-only'

import * as organizationsRepo from '@/server/repositories/organizations'
import { authorize, requireUser } from '@/server/policies/authorize'
import type {
  CreateOrganizationInput,
  UpdateOrganizationInput,
} from '@/server/schemas/organization'

/**
 * Servicios de organización: reglas de negocio y orquestación.
 * No hablan SQL (eso es el repositorio) ni saben de HTTP (eso son las actions).
 */

export async function createOrganization(input: CreateOrganizationInput): Promise<string> {
  // Cualquier usuario autenticado puede crear su organización: es el alta.
  await requireUser()

  return organizationsRepo.create({
    legalName: input.legalName,
    tradeName: input.tradeName?.trim() || null,
    rut: input.rut,
    capabilities: input.capabilities,
    countryCode: input.countryCode,
  })
}

export async function updateOrganization(input: UpdateOrganizationInput) {
  await authorize('organization.update', input.organizationId)

  const emptyToNull = (value: string | undefined) => (value?.trim() ? value.trim() : null)

  return organizationsRepo.update(input.organizationId, {
    legal_name: input.legalName,
    trade_name: emptyToNull(input.tradeName),
    short_description: emptyToNull(input.shortDescription),
    description: emptyToNull(input.description),
    value_proposition: emptyToNull(input.valueProposition),
    website_url: emptyToNull(input.websiteUrl),
    linkedin_url: emptyToNull(input.linkedinUrl),
    general_email: emptyToNull(input.generalEmail),
    general_phone: emptyToNull(input.generalPhone),
    founded_year: input.foundedYear ?? null,
    company_size: input.companySize ?? null,
    employee_count: input.employeeCount ?? null,
    visibility: input.visibility,
  })
}

/**
 * Publica el perfil: pasa de DRAFT a ACTIVE.
 *
 * Puerta de calidad mínima — un perfil incompleto en el directorio perjudica
 * al proveedor (nadie lo contacta) y al comprador (resultados con ruido).
 */
export async function publishOrganization(organizationId: string) {
  await authorize('organization.update', organizationId)

  const org = await organizationsRepo.findById(organizationId)
  if (!org) throw new Error('Organización no encontrada')

  const missing: string[] = []
  if (!org.short_description) missing.push('descripción corta')
  if (!org.description) missing.push('descripción corporativa')
  if (!org.trade_name) missing.push('nombre comercial')

  const identifier = await organizationsRepo.getPrimaryLegalIdentifier(organizationId)
  if (!identifier) missing.push('RUT')

  if (missing.length > 0) {
    throw new Error(`Faltan datos para publicar el perfil: ${missing.join(', ')}`)
  }

  return organizationsRepo.update(organizationId, { status: 'ACTIVE' })
}
