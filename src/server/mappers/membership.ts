import type { Views, OrganizationStatus, VisibilityLevel } from '@/lib/supabase/database.types'

/**
 * Membresía tal como la consume la UI.
 *
 * Postgres NO propaga `NOT NULL` a través de una vista: aunque
 * `organizations.id` sea not null, `v_my_organizations.id` se tipa como
 * `string | null`. Es correcto por parte del generador y no hay forma de
 * declararlo en la vista.
 *
 * En vez de esparcir `?? ''` por doce componentes, la fila cruda se estrecha
 * aquí una sola vez. Esta es la frontera que la arquitectura llama `mappers`:
 * a partir de aquí la UI trabaja con un tipo de dominio, no con una fila.
 */
export interface Membership {
  id: string
  legalName: string
  tradeName: string | null
  displayName: string
  slug: string
  status: OrganizationStatus
  visibility: VisibilityLevel
  completionPct: number
  memberId: string
  roleCodes: string[]
  capabilities: string[]
}

type MembershipRow = Views<'v_my_organizations'>

/**
 * Devuelve null si la fila no trae identificador: una fila así no es
 * utilizable y es preferible descartarla en la frontera que dejar que
 * reviente tres capas más arriba.
 */
export function toMembership(row: MembershipRow): Membership | null {
  if (!row.id || !row.member_id) return null

  const legalName = row.legal_name ?? 'Sin nombre'

  return {
    id: row.id,
    legalName,
    tradeName: row.trade_name,
    displayName: row.trade_name ?? legalName,
    slug: row.slug ?? '',
    status: row.status ?? 'DRAFT',
    visibility: row.visibility ?? 'PRIVATE',
    completionPct: row.completion_pct ?? 0,
    memberId: row.member_id,
    roleCodes: row.role_codes ?? [],
    capabilities: row.capabilities ?? [],
  }
}

export function toMemberships(rows: MembershipRow[] | null): Membership[] {
  return (rows ?? []).map(toMembership).filter((m): m is Membership => m !== null)
}
