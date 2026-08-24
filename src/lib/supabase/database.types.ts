/**
 * Tipos de la base de datos.
 *
 * ⚠️  ARCHIVO GENERADO — no editar a mano.
 *     Regenerar con: npm run db:types:remote
 *
 * Generado por scripts/db-gen-types.mjs leyendo el catálogo de Postgres.
 * No usa `supabase gen types` porque ese comando exige Docker incluso con
 * --db-url, y además ignora los ENUMs del schema `app`.
 */

export type Json = string | number | boolean | null | { [key: string]: Json | undefined } | Json[]

export type CompanySize = 'MICRO' | 'SMALL' | 'MEDIUM' | 'LARGE' | 'ENTERPRISE'
export type ContactType =
  | 'GENERAL'
  | 'COMERCIAL'
  | 'VENTAS'
  | 'GERENCIA'
  | 'OPERACIONES'
  | 'ABASTECIMIENTO'
  | 'CONTRATOS'
  | 'FINANZAS'
  | 'RRHH'
  | 'HSE'
  | 'ADMINISTRADOR_CONTRATO'
  | 'SOPORTE_TECNICO'
export type InvitationStatus = 'PENDING' | 'ACCEPTED' | 'EXPIRED' | 'REVOKED'
export type LocationType =
  | 'HEADQUARTERS'
  | 'BRANCH'
  | 'OPERATIONAL_BASE'
  | 'WAREHOUSE'
  | 'PLANT'
  | 'OFFICE'
export type MemberStatus = 'INVITED' | 'ACTIVE' | 'SUSPENDED' | 'REMOVED'
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
export type OrganizationCapability = 'BUYER' | 'SUPPLIER' | 'PLATFORM_ADMIN'
export type OrganizationStatus = 'DRAFT' | 'ACTIVE' | 'SUSPENDED' | 'ARCHIVED'
export type RevenueBand =
  | 'UNDER_2400_UF'
  | 'UF_2400_25000'
  | 'UF_25000_100000'
  | 'UF_100000_1000000'
  | 'OVER_1000000_UF'
  | 'UNDISCLOSED'
export type RoleScope = 'PLATFORM' | 'ORGANIZATION'
export type VisibilityLevel = 'PUBLIC' | 'REGISTERED' | 'BUYERS_ONLY' | 'INVITED_ONLY' | 'PRIVATE'

export type Database = {
  public: {
    Tables: {
      audit_logs: {
        Row: {
          id: number
          occurred_at: string
          actor_id: string | null
          organization_id: string | null
          action: string
          entity_type: string
          entity_id: string | null
          previous_value: Json | null
          new_value: Json | null
          ip_address: string | null
          user_agent: string | null
          request_id: string | null
          reason: string | null
        }
        Insert: {
          id?: number
          occurred_at?: string
          actor_id?: string | null
          organization_id?: string | null
          action: string
          entity_type: string
          entity_id?: string | null
          previous_value?: Json | null
          new_value?: Json | null
          ip_address?: string | null
          user_agent?: string | null
          request_id?: string | null
          reason?: string | null
        }
        Update: {
          id?: number
          occurred_at?: string
          actor_id?: string | null
          organization_id?: string | null
          action?: string
          entity_type?: string
          entity_id?: string | null
          previous_value?: Json | null
          new_value?: Json | null
          ip_address?: string | null
          user_agent?: string | null
          request_id?: string | null
          reason?: string | null
        }
      Relationships: []
      }
      domain_events: {
        Row: {
          id: number
          event_type: string
          aggregate_type: string
          aggregate_id: string | null
          organization_id: string | null
          payload: Json
          occurred_at: string
          processed_at: string | null
          attempts: number
          last_error: string | null
        }
        Insert: {
          id?: number
          event_type: string
          aggregate_type: string
          aggregate_id?: string | null
          organization_id?: string | null
          payload?: Json
          occurred_at?: string
          processed_at?: string | null
          attempts?: number
          last_error?: string | null
        }
        Update: {
          id?: number
          event_type?: string
          aggregate_type?: string
          aggregate_id?: string | null
          organization_id?: string | null
          payload?: Json
          occurred_at?: string
          processed_at?: string | null
          attempts?: number
          last_error?: string | null
        }
      Relationships: []
      }
      member_roles: {
        Row: {
          member_id: string
          role_id: string
          assigned_at: string
          assigned_by: string | null
        }
        Insert: {
          member_id: string
          role_id: string
          assigned_at?: string
          assigned_by?: string | null
        }
        Update: {
          member_id?: string
          role_id?: string
          assigned_at?: string
          assigned_by?: string | null
        }
      Relationships: [
        {
          foreignKeyName: 'member_roles_assigned_by_fkey'
          columns: ['assigned_by']
          isOneToOne: false
          referencedRelation: 'profiles'
          referencedColumns: ['id']
        },
        {
          foreignKeyName: 'member_roles_member_id_fkey'
          columns: ['member_id']
          isOneToOne: false
          referencedRelation: 'organization_members'
          referencedColumns: ['id']
        },
        {
          foreignKeyName: 'member_roles_role_id_fkey'
          columns: ['role_id']
          isOneToOne: false
          referencedRelation: 'roles'
          referencedColumns: ['id']
        },
      ]
      }
      organization_business_roles: {
        Row: {
          organization_id: string
          business_role: OrganizationBusinessRole
        }
        Insert: {
          organization_id: string
          business_role: OrganizationBusinessRole
        }
        Update: {
          organization_id?: string
          business_role?: OrganizationBusinessRole
        }
      Relationships: [
        {
          foreignKeyName: 'organization_business_roles_organization_id_fkey'
          columns: ['organization_id']
          isOneToOne: false
          referencedRelation: 'organizations'
          referencedColumns: ['id']
        },
      ]
      }
      organization_capabilities: {
        Row: {
          organization_id: string
          capability: OrganizationCapability
          enabled_at: string
          enabled_by: string | null
        }
        Insert: {
          organization_id: string
          capability: OrganizationCapability
          enabled_at?: string
          enabled_by?: string | null
        }
        Update: {
          organization_id?: string
          capability?: OrganizationCapability
          enabled_at?: string
          enabled_by?: string | null
        }
      Relationships: [
        {
          foreignKeyName: 'organization_capabilities_enabled_by_fkey'
          columns: ['enabled_by']
          isOneToOne: false
          referencedRelation: 'profiles'
          referencedColumns: ['id']
        },
        {
          foreignKeyName: 'organization_capabilities_organization_id_fkey'
          columns: ['organization_id']
          isOneToOne: false
          referencedRelation: 'organizations'
          referencedColumns: ['id']
        },
      ]
      }
      organization_invitations: {
        Row: {
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
        Insert: {
          id?: string
          organization_id: string
          email: string
          role_id: string
          token_hash: string
          status?: InvitationStatus
          invited_by: string
          expires_at: string
          accepted_at?: string | null
          accepted_by?: string | null
          revoked_at?: string | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          organization_id?: string
          email?: string
          role_id?: string
          token_hash?: string
          status?: InvitationStatus
          invited_by?: string
          expires_at?: string
          accepted_at?: string | null
          accepted_by?: string | null
          revoked_at?: string | null
          created_at?: string
          updated_at?: string
        }
      Relationships: [
        {
          foreignKeyName: 'organization_invitations_accepted_by_fkey'
          columns: ['accepted_by']
          isOneToOne: false
          referencedRelation: 'profiles'
          referencedColumns: ['id']
        },
        {
          foreignKeyName: 'organization_invitations_invited_by_fkey'
          columns: ['invited_by']
          isOneToOne: false
          referencedRelation: 'profiles'
          referencedColumns: ['id']
        },
        {
          foreignKeyName: 'organization_invitations_organization_id_fkey'
          columns: ['organization_id']
          isOneToOne: false
          referencedRelation: 'organizations'
          referencedColumns: ['id']
        },
        {
          foreignKeyName: 'organization_invitations_role_id_fkey'
          columns: ['role_id']
          isOneToOne: false
          referencedRelation: 'roles'
          referencedColumns: ['id']
        },
      ]
      }
      organization_legal_identifiers: {
        Row: {
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
        Insert: {
          id?: string
          organization_id: string
          identifier_type: string
          country_code?: string | null
          value: string
          value_normalized: string
          is_primary?: boolean
          verified_at?: string | null
          verified_by?: string | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          organization_id?: string
          identifier_type?: string
          country_code?: string | null
          value?: string
          value_normalized?: string
          is_primary?: boolean
          verified_at?: string | null
          verified_by?: string | null
          created_at?: string
          updated_at?: string
        }
      Relationships: [
        {
          foreignKeyName: 'organization_legal_identifiers_organization_id_fkey'
          columns: ['organization_id']
          isOneToOne: false
          referencedRelation: 'organizations'
          referencedColumns: ['id']
        },
        {
          foreignKeyName: 'organization_legal_identifiers_verified_by_fkey'
          columns: ['verified_by']
          isOneToOne: false
          referencedRelation: 'profiles'
          referencedColumns: ['id']
        },
      ]
      }
      organization_members: {
        Row: {
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
        Insert: {
          id?: string
          user_id: string
          organization_id: string
          status?: MemberStatus
          approval_limit_amount?: number | null
          approval_limit_currency?: string | null
          invited_by?: string | null
          invited_at?: string | null
          joined_at?: string
          removed_at?: string | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          user_id?: string
          organization_id?: string
          status?: MemberStatus
          approval_limit_amount?: number | null
          approval_limit_currency?: string | null
          invited_by?: string | null
          invited_at?: string | null
          joined_at?: string
          removed_at?: string | null
          created_at?: string
          updated_at?: string
        }
      Relationships: [
        {
          foreignKeyName: 'organization_members_invited_by_fkey'
          columns: ['invited_by']
          isOneToOne: false
          referencedRelation: 'profiles'
          referencedColumns: ['id']
        },
        {
          foreignKeyName: 'organization_members_organization_id_fkey'
          columns: ['organization_id']
          isOneToOne: false
          referencedRelation: 'organizations'
          referencedColumns: ['id']
        },
        {
          foreignKeyName: 'organization_members_user_id_fkey'
          columns: ['user_id']
          isOneToOne: false
          referencedRelation: 'profiles'
          referencedColumns: ['id']
        },
      ]
      }
      organizations: {
        Row: {
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
        Insert: {
          id?: string
          legal_name: string
          trade_name?: string | null
          slug: string
          country_code?: string
          founded_year?: number | null
          company_size?: CompanySize | null
          employee_count?: number | null
          revenue_band?: RevenueBand
          legal_form?: string | null
          short_description?: string | null
          description?: string | null
          value_proposition?: string | null
          website_url?: string | null
          linkedin_url?: string | null
          general_email?: string | null
          general_phone?: string | null
          status?: OrganizationStatus
          visibility?: VisibilityLevel
          is_claimed?: boolean
          data_source?: string
          verified_at?: string | null
          verified_by?: string | null
          completion_pct?: number
          created_at?: string
          updated_at?: string
          created_by?: string | null
          updated_by?: string | null
          deleted_at?: string | null
        }
        Update: {
          id?: string
          legal_name?: string
          trade_name?: string | null
          slug?: string
          country_code?: string
          founded_year?: number | null
          company_size?: CompanySize | null
          employee_count?: number | null
          revenue_band?: RevenueBand
          legal_form?: string | null
          short_description?: string | null
          description?: string | null
          value_proposition?: string | null
          website_url?: string | null
          linkedin_url?: string | null
          general_email?: string | null
          general_phone?: string | null
          status?: OrganizationStatus
          visibility?: VisibilityLevel
          is_claimed?: boolean
          data_source?: string
          verified_at?: string | null
          verified_by?: string | null
          completion_pct?: number
          created_at?: string
          updated_at?: string
          created_by?: string | null
          updated_by?: string | null
          deleted_at?: string | null
        }
      Relationships: [
        {
          foreignKeyName: 'organizations_created_by_fkey'
          columns: ['created_by']
          isOneToOne: false
          referencedRelation: 'profiles'
          referencedColumns: ['id']
        },
        {
          foreignKeyName: 'organizations_updated_by_fkey'
          columns: ['updated_by']
          isOneToOne: false
          referencedRelation: 'profiles'
          referencedColumns: ['id']
        },
        {
          foreignKeyName: 'organizations_verified_by_fkey'
          columns: ['verified_by']
          isOneToOne: false
          referencedRelation: 'profiles'
          referencedColumns: ['id']
        },
      ]
      }
      permissions: {
        Row: {
          code: string
          resource: string
          action: string
          description: string
          scope: RoleScope
        }
        Insert: {
          code: string
          resource: string
          action: string
          description: string
          scope?: RoleScope
        }
        Update: {
          code?: string
          resource?: string
          action?: string
          description?: string
          scope?: RoleScope
        }
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
        Insert: {
          user_id: string
          role_id: string
          granted_at?: string
          granted_by?: string | null
          revoked_at?: string | null
        }
        Update: {
          user_id?: string
          role_id?: string
          granted_at?: string
          granted_by?: string | null
          revoked_at?: string | null
        }
      Relationships: [
        {
          foreignKeyName: 'platform_admins_granted_by_fkey'
          columns: ['granted_by']
          isOneToOne: false
          referencedRelation: 'profiles'
          referencedColumns: ['id']
        },
        {
          foreignKeyName: 'platform_admins_role_id_fkey'
          columns: ['role_id']
          isOneToOne: false
          referencedRelation: 'roles'
          referencedColumns: ['id']
        },
        {
          foreignKeyName: 'platform_admins_user_id_fkey'
          columns: ['user_id']
          isOneToOne: false
          referencedRelation: 'profiles'
          referencedColumns: ['id']
        },
      ]
      }
      profiles: {
        Row: {
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
        Insert: {
          id: string
          first_name?: string | null
          last_name?: string | null
          avatar_url?: string | null
          phone?: string | null
          job_title?: string | null
          locale?: string
          timezone?: string
          last_org_id?: string | null
          onboarded_at?: string | null
          last_active_at?: string | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          first_name?: string | null
          last_name?: string | null
          avatar_url?: string | null
          phone?: string | null
          job_title?: string | null
          locale?: string
          timezone?: string
          last_org_id?: string | null
          onboarded_at?: string | null
          last_active_at?: string | null
          created_at?: string
          updated_at?: string
        }
      Relationships: [
        {
          foreignKeyName: 'profiles_id_fkey'
          columns: ['id']
          isOneToOne: false
          referencedRelation: 'users'
          referencedColumns: ['id']
        },
        {
          foreignKeyName: 'profiles_last_org_id_fkey'
          columns: ['last_org_id']
          isOneToOne: false
          referencedRelation: 'organizations'
          referencedColumns: ['id']
        },
      ]
      }
      role_permissions: {
        Row: {
          role_id: string
          permission_code: string
          granted_at: string
        }
        Insert: {
          role_id: string
          permission_code: string
          granted_at?: string
        }
        Update: {
          role_id?: string
          permission_code?: string
          granted_at?: string
        }
      Relationships: [
        {
          foreignKeyName: 'role_permissions_permission_code_fkey'
          columns: ['permission_code']
          isOneToOne: false
          referencedRelation: 'permissions'
          referencedColumns: ['code']
        },
        {
          foreignKeyName: 'role_permissions_role_id_fkey'
          columns: ['role_id']
          isOneToOne: false
          referencedRelation: 'roles'
          referencedColumns: ['id']
        },
      ]
      }
      roles: {
        Row: {
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
        Insert: {
          id?: string
          code: string
          name: string
          description?: string | null
          scope: RoleScope
          organization_id?: string | null
          is_system?: boolean
          is_default_owner?: boolean
          sort_order?: number
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          code?: string
          name?: string
          description?: string | null
          scope?: RoleScope
          organization_id?: string | null
          is_system?: boolean
          is_default_owner?: boolean
          sort_order?: number
          created_at?: string
          updated_at?: string
        }
      Relationships: [
        {
          foreignKeyName: 'roles_organization_id_fkey'
          columns: ['organization_id']
          isOneToOne: false
          referencedRelation: 'organizations'
          referencedColumns: ['id']
        },
      ]
      }
    }
    Views: {
      v_my_organizations: {
        Row: {
          id: string | null
          legal_name: string | null
          trade_name: string | null
          slug: string | null
          status: OrganizationStatus | null
          visibility: VisibilityLevel | null
          completion_pct: number | null
          member_id: string | null
          member_status: MemberStatus | null
          joined_at: string | null
          role_codes: string[] | null
          capabilities: string[] | null
        }
      Relationships: []
      }
    }
    Functions: {
      accept_invitation: {
        Args: {
          p_token: string
        }
        Returns: string
      }
      am_i_platform_admin: {
        Args: Record<string, never>
        Returns: unknown
      }
      create_organization: {
        Args: {
          p_legal_name: string
          p_trade_name?: string
          p_rut?: string
          p_capabilities?: OrganizationCapability[]
          p_country_code?: string
        }
        Returns: string
      }
      my_permissions: {
        Args: {
          p_organization_id: string
        }
        Returns: string[]
      }
      remove_member: {
        Args: {
          p_member_id: string
        }
        Returns: undefined
      }
      switch_organization: {
        Args: {
          p_organization_id: string
        }
        Returns: undefined
      }
    }
    Enums: {
      company_size: CompanySize
      contact_type: ContactType
      invitation_status: InvitationStatus
      location_type: LocationType
      member_status: MemberStatus
      organization_business_role: OrganizationBusinessRole
      organization_capability: OrganizationCapability
      organization_status: OrganizationStatus
      revenue_band: RevenueBand
      role_scope: RoleScope
      visibility_level: VisibilityLevel
    }
    CompositeTypes: Record<string, never>
  }
}

export type Tables<T extends keyof Database['public']['Tables']> =
  Database['public']['Tables'][T]['Row']
export type Views<T extends keyof Database['public']['Views']> =
  Database['public']['Views'][T]['Row']
