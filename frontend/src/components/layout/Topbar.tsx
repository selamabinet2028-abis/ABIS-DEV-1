import { useNavigate } from 'react-router-dom'

import { useAuthStore } from '../../stores/auth'

export function Topbar() {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  const displayName =
    user && (user.first_name || user.last_name)
      ? `${user.first_name} ${user.last_name}`.trim()
      : (user?.username ?? '')

  return (
    <header className="flex h-14 items-center justify-between border-b border-slate-200 bg-white px-6">
      <div className="text-sm font-medium text-slate-500">
        Automated Biometric Identification System
      </div>
      <div className="flex items-center gap-4">
        <div className="text-right">
          <div className="text-sm font-medium text-slate-800">{displayName}</div>
          <div className="text-xs uppercase tracking-wide text-slate-400">{user?.role}</div>
        </div>
        <button
          type="button"
          onClick={handleLogout}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100"
        >
          Sign out
        </button>
      </div>
    </header>
  )
}
