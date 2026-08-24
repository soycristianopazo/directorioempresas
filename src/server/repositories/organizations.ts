import 'server-only'

import { createClient } from '@/lib/supabase/server'
import type { Tables } from '@/lib/supabase/database.types'

/**
 * Repositorio de organizaciones.
 *
 * Único lugar del proyecto que habla SQL sobre este agregado. Todas las
 * consultas usan el cliente con clave anónima, así que RLS sigue aplicando:
 * este repositorio no puede ver más de lo que el usuario puede ver.
 */

export type Organization = Tables<'organizations'>

export async function findById(id: string): Promise<Organization | null> {
  const supabase = await createClient()
  const { data, error } = await supabase
    .from('organizations')
    .select('*')
    .eq('id', id)
    .is('deleted_at', null)
    .maybeSingle()

  if (error) throw error
  return data
}

export async function findBySlug(slug: string): Promise<Organization | null> {
  const supabase = await createClient()
  const { data, error } = await supabase
    .from('organizations')
    .select('*')
    .eq('slug', slug)
    .is('deleted_at', null)
    .maybeSingle()

  if (error) throw error
  return data
}

export interface CreateOrganizationParams {
  legalName: string
  tradeName?: string | null
  rut?: string | null
  capabilities: ('BUYER' | 'SUPPLIER')[]
  countryCode?: string
}

/**
 * Crea la organización vía RPC transaccional.
 *
 * No es un INSERT: `create_organization` crea también la membresía y el rol de
 * dueño en la misma transacción. Ver migración 0009.
 */
export async function create(params: CreateOrganizationParams): Promise<string> {
  const supabase = await createClient()

  const { data, error } = await supabase.rpc('create_organization', {
    p_legal_name: params.legalName,
    p_trade_name: params.tradeName ?? undefined,
    p_rut: params.rut ?? undefined,
    p_capabilities: params.capabilities,
    p_country_code: params.countryCode ?? 'CL',
  })

  if (error) throw error
  if (!data) throw new Error('create_organization no devolvió un identificador')

  return data
}

export async function update(
  id: string,
  patch: Partial<Omit<Organization, 'id' | 'created_at' | 'slug'>>,
): Promise<Organization> {
  const supabase = await createClient()

  const { data, error } = await supabase
    .from('organizations')
    .update(patch)
    .eq('id', id)
    .is('deleted_at', null)
    .select('*')
    .single()

  if (error) throw error
  return data
}

export async function listCapabilities(organizationId: string): Promise<string[]> {
  const supabase = await createClient()
  const { data, error } = await supabase
    .from('organization_capabilities')
    .select('capability')
    .eq('organization_id', organizationId)

  if (error) throw error
  return (data ?? []).map((r) => r.capability)
}

export async function getPrimaryLegalIdentifier(
  organizationId: string,
): Promise<{ identifier_type: string; value: string } | null> {
  const supabase = await createClient()
  const { data, error } = await supabase
    .from('organization_legal_identifiers')
    .select('identifier_type, value')
    .eq('organization_id', organizationId)
    .eq('is_primary', true)
    .maybeSingle()

  if (error) throw error
  return data
}
