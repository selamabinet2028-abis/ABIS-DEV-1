import { useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { apiErrorMessage } from '../api/client'
import { useAuthStore } from '../stores/auth'

export function LoginPage() {
  const login = useAuthStore((s) => s.login)
  const status = useAuthStore((s) => s.status)
  const navigate = useNavigate()
  const location = useLocation()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    if (!username.trim() || !password) {
      setError('Username and password are required')
      return
    }
    try {
      await login(username.trim(), password)
      const from = (location.state as { from?: string } | null)?.from
      navigate(from ?? '/', { replace: true })
    } catch (err) {
      setError(apiErrorMessage(err, 'Login failed'))
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-900 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center gap-3">
          <img src="/abis.svg" alt="ABIS logo" className="h-16 w-16" />
          <div className="text-center">
            <h1 className="text-xl font-bold tracking-wide text-white">ABIS</h1>
            <p className="text-xs uppercase tracking-widest text-slate-400">
              Ethiopian Federal Police Commission
            </p>
          </div>
        </div>

        <form
          onSubmit={handleSubmit}
          className="space-y-4 rounded-xl bg-white p-6 shadow-xl"
          aria-label="Sign in"
        >
          <h2 className="text-lg font-semibold text-slate-800">Sign in</h2>

          {error && (
            <div role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          <div>
            <label htmlFor="username" className="mb-1 block text-sm font-medium text-slate-700">
              Username
            </label>
            <input
              id="username"
              name="username"
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600"
            />
          </div>

          <div>
            <label htmlFor="password" className="mb-1 block text-sm font-medium text-slate-700">
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600"
            />
          </div>

          <button
            type="submit"
            disabled={status === 'authenticating'}
            className="w-full rounded-md bg-blue-700 py-2 text-sm font-medium text-white hover:bg-blue-800 disabled:opacity-60"
          >
            {status === 'authenticating' ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className="mt-6 text-center text-xs text-slate-500">
          Authorized personnel only. All activity is audited.
        </p>
      </div>
    </div>
  )
}
