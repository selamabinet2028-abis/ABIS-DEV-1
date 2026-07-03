import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'

import { useAuthStore } from '../stores/auth'

export const API_BASE = '/api/v1'

/** URLs that must never trigger a token refresh on 401. */
const AUTH_URLS = ['/auth/login/', '/auth/refresh/', '/auth/logout/']

export const client = axios.create({
  baseURL: API_BASE,
  withCredentials: true, // refresh token cookie (ADR-006)
  headers: { 'Content-Type': 'application/json' },
})

client.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

/** Single-flight refresh: concurrent 401s share one refresh request. */
let refreshInFlight: Promise<string> | null = null

async function refreshAccessToken(): Promise<string> {
  // Bare axios instance — must not recurse through the interceptors.
  const { data } = await axios.post<{ access: string }>(
    `${API_BASE}/auth/refresh/`,
    {},
    { withCredentials: true },
  )
  useAuthStore.getState().setAccessToken(data.access)
  return data.access
}

interface RetriableConfig extends InternalAxiosRequestConfig {
  _retry?: boolean
}

client.interceptors.response.use(undefined, async (error: AxiosError) => {
  const original = error.config as RetriableConfig | undefined
  const isAuthUrl = AUTH_URLS.some((u) => original?.url?.includes(u))

  if (error.response?.status === 401 && original && !original._retry && !isAuthUrl) {
    original._retry = true
    try {
      refreshInFlight ??= refreshAccessToken().finally(() => {
        refreshInFlight = null
      })
      const token = await refreshInFlight
      original.headers.Authorization = `Bearer ${token}`
      return client(original)
    } catch {
      useAuthStore.getState().clearSession()
    }
  }
  return Promise.reject(error)
})

/** Extract a human-readable message from a DRF error response. */
export function apiErrorMessage(error: unknown, fallback = 'Something went wrong'): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as { detail?: string } | undefined
    if (data?.detail) return data.detail
    if (error.response?.status === 429) return 'Too many attempts — try again shortly'
    if (!error.response) return 'Cannot reach the server'
  }
  return fallback
}
