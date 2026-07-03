import { useLocation } from 'react-router-dom'

import { NAV_ITEMS } from '../components/layout/nav'

/** Stands in for feature pages until T-018 builds them. */
export function ModulePlaceholderPage() {
  const { pathname } = useLocation()
  const item = NAV_ITEMS.find((i) => i.to === pathname)

  return (
    <div className="flex h-full flex-col items-center justify-center text-center">
      <div className="text-4xl">🚧</div>
      <h1 className="mt-3 text-lg font-semibold text-slate-700">
        {item?.label ?? 'Module'} — under construction
      </h1>
      <p className="mt-1 max-w-md text-sm text-slate-500">
        This module is scheduled in the task queue and will appear here once its
        backend endpoints and pages are built.
      </p>
    </div>
  )
}
