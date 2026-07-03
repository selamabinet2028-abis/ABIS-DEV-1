import { useAuthStore } from '../stores/auth'

/** Placeholder dashboard — live KPIs and charts land with T-016/T-018. */
export function DashboardPage() {
  const user = useAuthStore((s) => s.user)

  const placeholders = [
    'Enrollments today',
    'Pending applications',
    'Running match jobs',
    'Open alerts',
  ]

  return (
    <div>
      <h1 className="text-xl font-semibold text-slate-800">
        Welcome{user?.first_name ? `, ${user.first_name}` : ''}
      </h1>
      <p className="mt-1 text-sm text-slate-500">
        Operational overview. Live figures appear once reporting is connected.
      </p>
      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {placeholders.map((label) => (
          <div key={label} className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
            <div className="mt-2 text-2xl font-bold text-slate-300">—</div>
          </div>
        ))}
      </div>
    </div>
  )
}
