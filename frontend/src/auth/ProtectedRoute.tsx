import { useEffect } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useAuthStore } from '../stores/auth'
import type { RoleName } from '../types/auth'

/** Gate for authenticated routes. On first mount with a cold store it attempts
 *  a silent session restore (refresh cookie) before deciding. */
export function ProtectedRoute({ allowedRoles }: { allowedRoles?: RoleName[] }) {
  const status = useAuthStore((s) => s.status)
  const user = useAuthStore((s) => s.user)
  const bootstrap = useAuthStore((s) => s.bootstrap)
  const location = useLocation()

  useEffect(() => {
    if (status === 'idle') {
      void bootstrap()
    }
  }, [status, bootstrap])

  if (status === 'idle' || status === 'authenticating') {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-100">
        <div className="text-sm text-slate-500">Loading…</div>
      </div>
    )
  }

  if (status !== 'authenticated') {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  if (allowedRoles && (!user?.role || !allowedRoles.includes(user.role))) {
    return (
      <div className="p-8">
        <h1 className="text-lg font-semibold text-slate-800">Access denied</h1>
        <p className="mt-1 text-sm text-slate-500">
          Your role does not permit access to this page.
        </p>
      </div>
    )
  }

  return <Outlet />
}
