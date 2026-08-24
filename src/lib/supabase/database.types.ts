/**
 * Tipos de la base de datos.
 *
 * ⚠️  ARCHIVO GENERADO — no editar a mano.
 *     Regenerar con:  npm run db:types        (contra Supabase local)
 *                     npm run db:types:remote (contra el proyecto enlazado)
 *
 * Esta versión inicial está escrita a mano para que el proyecto compile antes
 * de tener una base levantada. En cuanto exista, el comando la sobrescribe.
 */

export type Json = string | number | boolean | null | { [key: string]: Json | undefined } | Json[]

export type VisibilityLevel = 'PUBLIC' | 'REGISTERED' | 'BUYERS_ONLY' | 'INVITED_ONLY' | 'PRIVATE'
export type OrganizationCapability = 'BUYER' | 'SUPPLIER' | 'PLATFORM_ADMIN'
export type OrganizationStatus = 'DRAFT' | 'ACTIVE' | 'SUSPENDED' | 'ARCHIVED'
export type MemberStatus = 'INVITED' | 'ACTIVE' | 'SUSPENDED' | 'REMOVED'
export type RoleScope = 'PLATFORM' | 'ORGANIZATION'
export type InvitationStatus = 'PENDING' | 'ACCEPTED' | 'EXPIRED' | 'REVOKED'
export type CompanySize = 'MICRO' | 'SMALL' | 'MEDIUM' | 'LARGE' | 'ENTERPRISE'
export type RevenueBand =
  | 'UNDER_2400_UF'
  | 'UF_2400_25000'
  | 'UF_25000_100000'
  | 'UF_100000_1000000'
  | 'OVER_1000000_UF'
  | 'UNDISCLOSED'
export type OrganizationBusinessRole =
  | 'MANDANTE'
  | 'CONTRATISTA'
  | 'SUBCONTRATISTA'
  | 'FABRICANTE'
  | 'DISTRIBUIDOR'
  | 'REPRESENTANTE'
  | 'CONSULTORA'
  | 'OTEC'
  | 'SERVICIOS_PROFESIONALES'

type ProfileRow = {
  id: string
  first_name: string | null
  last_name: string | null
  full_name: string | null
  avatar_url: string | null
  phone: string | null
  job_title: string | null
  locale: string
  timezone: string
  last_org_id: string | null
  onboarded_at: string | null
  last_active_at: string | null
  created_at: string
  updated_at: string
}

type OrganizationRow = {
  id: string
  legal_name: string
  trade_name: string | null
  slug: string
  country_code: string
  founded_year: number | null
  company_size: CompanySize | null
  employee_count: number | null
  revenue_band: RevenueBand
  legal_form: string | null
  short_description: string | null
  description: string | null
  value_proposition: string | null
  website_url: string | null
  linkedin_url: string | null
  general_email: string | null
  general_phone: string | null
  status: OrganizationStatus
  visibility: VisibilityLevel
  is_claimed: boolean
  data_source: string
  verified_at: string | null
  verified_by: string | null
  completion_pct: number
  created_at: string
  updated_at: string
  created_by: string | null
  updated_by: string | null
  deleted_at: string | null
}

type OrganizationMemberRow = {
  id: string
  user_id: string
  organization_id: string
  status: MemberStatus
  approval_limit_amount: number | null
  approval_limit_currency: string | null
  invited_by: string | null
  invited_at: string | null
  joined_at: string
  removed_at: string | null
  created_at: string
  updated_at: string
}

type RoleRow = {
  id: string
  code: string
  name: string
  description: string | null
  scope: RoleScope
  organization_id: string | null
  is_system: boolean
  is_default_owner: boolean
  sort_order: number
  created_at: string
  updated_at: string
}

type PermissionRow = {
  code: string
  resource: string
  action: string
  description: string
  scope: RoleScope
}

type OrganizationInvitationRow = {
  id: string
  organization_id: string
  email: string
  role_id: string
  token_hash: string
  status: InvitationStatus
  invited_by: string
  expires_at: string
  accepted_at: string | null
  accepted_by: string | null
  revoked_at: string | null
  created_at: string
  updated_at: string
}

type OrganizationLegalIdentifierRow = {
  id: string
  organization_id: string
  identifier_type: string
  country_code: string | null
  value: string
  value_normalized: string
  is_primary: boolean
  verified_at: string | null
  verified_by: string | null
  created_at: string
  updated_at: string
}

type Writable<T> = Omit<T, 'created_at' | 'updated_at'> & {
  created_at?: string
  updated_at?: string
}

export type Database = {
  public: {
    Tables: {
      profiles: {
        Row: ProfileRow
        Insert: Partial<Writable<ProfileRow>> & { id: string }
        Update: Partial<Writable<ProfileRow>>
        Relationships: []
      }
      organizations: {
        Row: OrganizationRow
        Insert: Partial<Writable<OrganizationRow>> & { legal_name: string; slug: string }
        Update: Partial<Writable<OrganizationRow>>
        Relationships: []
      }
      organization_capabilities: {
        Row: {
          organization_id: string
          capability: OrganizationCapability
          enabled_at: string
          enabled_by: string | null
        }
        Insert: { organization_id: string; capability: OrganizationCapability; enabled_by?: string }
        Update: { capability?: OrganizationCapability }
        Relationships: []
      }
      organization_business_roles: {
        Row: { organization_id: string; business_role: OrganizationBusinessRole }
        Insert: { organization_id: string; business_role: OrganizationBusinessRole }
        Update: { business_role?: OrganizationBusinessRole }
        Relationships: []
      }
      organization_legal_identifiers: {
        Row: OrganizationLegalIdentifierRow
        Insert: Partial<Writable<OrganizationLegalIdentifierRow>> & {
          organization_id: string
          identifier_type: string
          value: string
        }
        Update: Partial<Writable<OrganizationLegalIdentifierRow>>
        Relationships: []
      }
      organization_members: {
        Row: OrganizationMemberRow
        Insert: Partial<Writable<OrganizationMemberRow>> & {
          user_id: string
          organization_id: string
        }
        Update: Partial<Writable<OrganizationMemberRow>>
        Relationships: []
      }
      member_roles: {
        Row: {
          member_id: string
          role_id: string
          assigned_at: string
          assigned_by: string | null
        }
        Insert: { member_id: string; role_id: string; assigned_by?: string }
        Update: { role_id?: string }
        Relationships: []
      }
      roles: {
        Row: RoleRow
        Insert: Partial<Writable<RoleRow>> & { code: string; name: string; scope: RoleScope }
        Update: Partial<Writable<RoleRow>>
        Relationships: []
      }
      permissions: {
        Row: PermissionRow
        Insert: PermissionRow
        Update: Partial<PermissionRow>
        Relationships: []
      }
      role_permissions: {
        Row: { role_id: string; permission_code: string; granted_at: string }
        Insert: { role_id: string; permission_code: string }
        Update: Record<string, never>
        Relationships: []
      }
      organization_invitations: {
        Row: OrganizationInvitationRow
        Insert: Partial<Writable<OrganizationInvitationRow>> & {
          organization_id: string
          email: string
          role_id: string
          token_hash: string
          invited_by: string
          expires_at: string
        }
        Update: Partial<Writable<OrganizationInvitationRow>>
        Relationships: []
      }
      platform_admins: {
        Row: {
          user_id: string
          role_id: string
          granted_at: string
          granted_by: string | null
          revoked_at: string | null
        }
        Insert: { user_id: string; role_id: string; granted_by?: string }
        Update: { revoked_at?: string | null }
        Relationships: []
      }
    }
    Views: {
      v_my_organizations: {
        Row: {
          id: string
          legal_name: string
          trade_name: string | null
          slug: string
          status: OrganizationStatus
          visibility: VisibilityLevel
          completion_pct: number
          member_id: string
          member_status: MemberStatus
          joined_at: string
          role_codes: string[]
          capabilities: string[]
        }
        Relationships: []
      }
    }
    Functions: {
      create_organization: {
        Args: {
          p_legal_name: string
          p_trade_name?: string | null
          p_rut?: string | null
          p_capabilities?: OrganizationCapability[]
          p_country_code?: string
        }
        Returns: string
      }
      accept_invitation: {
        Args: { p_token: string }
        Returns: string
      }
      switch_organization: {
        Args: { p_organization_id: string }
        Returns: undefined
      }
      remove_member: {
        Args: { p_member_id: string }
        Returns: undefined
      }
      my_permissions: {
        Args: { p_organization_id: string }
        Returns: string[]
      }
      am_i_platform_admin: {
        Args: Record<string, never>
        Returns: boolean
      }
    }
    Enums: {
      visibility_level: VisibilityLevel
      organization_capability: OrganizationCapability
      organization_status: OrganizationStatus
      member_status: MemberStatus
      role_scope: RoleScope
      invitation_status: InvitationStatus
      company_size: CompanySize
      revenue_band: RevenueBand
    }
    CompositeTypes: Record<string, never>
  }
}

export type Tables<T extends keyof Database['public']['Tables']> =
  Database['public']['Tables'][T]['Row']
export type Views<T extends keyof Database['public']['Views']> =
  Database['public']['Views'][T]['Row']
