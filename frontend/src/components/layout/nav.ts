import type { RoleName } from '../../types/auth'

export interface NavItem {
  to: string
  label: string
  roles: RoleName[]
}

/** Role-aware navigation (ARCHITECTURE.md). Feature pages land with T-018;
 *  until then unknown module routes render a placeholder. */
export const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Dashboard', roles: ['admin', 'operator', 'investigator', 'supervisor', 'auditor'] },
  { to: '/persons', label: 'Persons', roles: ['admin', 'operator', 'investigator', 'supervisor'] },
  { to: '/enrollment', label: 'Enrollment', roles: ['admin', 'operator'] },
  { to: '/matching', label: 'Matching', roles: ['admin', 'investigator', 'supervisor'] },
  { to: '/cases', label: 'Investigations', roles: ['admin', 'investigator', 'supervisor'] },
  { to: '/pis', label: 'Photo Search', roles: ['admin', 'investigator', 'supervisor'] },
  { to: '/watchlists', label: 'Watchlists', roles: ['admin', 'investigator', 'supervisor'] },
  { to: '/applications', label: 'Applications', roles: ['admin', 'operator', 'supervisor'] },
  { to: '/appointments', label: 'Appointments', roles: ['admin', 'operator'] },
  { to: '/payments', label: 'Payments', roles: ['admin', 'operator', 'supervisor'] },
  { to: '/certificates', label: 'Certificates', roles: ['admin', 'operator', 'supervisor'] },
  { to: '/reports', label: 'Reports', roles: ['admin', 'supervisor', 'auditor'] },
  { to: '/audit-logs', label: 'Audit Logs', roles: ['admin', 'auditor'] },
  { to: '/users', label: 'Users & Roles', roles: ['admin'] },
]

export function navItemsForRole(role: RoleName | null): NavItem[] {
  if (!role) return []
  return NAV_ITEMS.filter((item) => item.roles.includes(role))
}
