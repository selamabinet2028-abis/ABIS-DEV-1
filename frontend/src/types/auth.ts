export const ROLES = ['admin', 'operator', 'investigator', 'supervisor', 'auditor'] as const

export type RoleName = (typeof ROLES)[number]

export interface User {
  id: string
  username: string
  first_name: string
  last_name: string
  email: string
  role: RoleName | null
  org_unit: string | null
  badge_number: string | null
}

/** Contract: POST /api/v1/auth/login/ (API_DOCUMENTATION.md). The refresh
 *  token travels in an httpOnly cookie per ADR-006; a `refresh` body field,
 *  if present, is ignored by the client. */
export interface LoginResponse {
  access: string
  user: User
}

export interface RefreshResponse {
  access: string
}
