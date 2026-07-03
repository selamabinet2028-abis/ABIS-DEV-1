import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-100 text-center">
      <div className="text-5xl font-bold text-slate-300">404</div>
      <p className="mt-2 text-sm text-slate-500">Page not found.</p>
      <Link to="/" className="mt-4 text-sm font-medium text-blue-700 hover:underline">
        Back to dashboard
      </Link>
    </div>
  )
}
