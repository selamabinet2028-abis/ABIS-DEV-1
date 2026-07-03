import { NavLink } from 'react-router-dom'

import { useAuthStore } from '../../stores/auth'
import { navItemsForRole } from './nav'

export function Sidebar() {
  const role = useAuthStore((s) => s.user?.role ?? null)
  const items = navItemsForRole(role)

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-slate-800 bg-slate-900">
      <div className="flex items-center gap-2 px-4 py-5">
        <img src="/abis.svg" alt="" className="h-8 w-8" />
        <div>
          <div className="text-sm font-bold tracking-wide text-white">ABIS</div>
          <div className="text-[10px] uppercase tracking-wider text-slate-400">
            Federal Police Commission
          </div>
        </div>
      </div>
      <nav aria-label="Main navigation" className="flex-1 space-y-0.5 overflow-y-auto px-2 pb-4">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `block rounded-md px-3 py-2 text-sm transition-colors ${
                isActive
                  ? 'bg-blue-700 font-medium text-white'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              }`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
