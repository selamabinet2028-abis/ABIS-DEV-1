import { create } from 'zustand'

import { apiLogin, apiLogout, apiMe, apiRefresh } from '../api/auth'
import type { User } from '../types/auth'

export type AuthStatus = 'idle' | 'authenticating' | 'authenticated' | 'unauthenticated'

interface AuthState {
  user: User | null
  /** Access token lives in memory only — never persisted (ADR-006). */
  accessToken: string | null
  status: AuthStatus
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  /** Silent session restore on app boot via the refresh cookie. */
  bootstrap: () => Promise<void>
  setAccessToken: (token: string) => void
  clearSession: () => void
}

export const useAuthStore = create<AuthState>()((set, get) => ({
  user: null,
  accessToken: null,
  status: 'idle',

  login: async (username, password) => {
    set({ status: 'authenticating' })
    try {
      const { access, user } = await apiLogin(username, password)
      set({ accessToken: access, user, status: 'authenticated' })
    } catch (error) {
      set({ user: null, accessToken: null, status: 'unauthenticated' })
      throw error
    }
  },

  logout: async () => {
    try {
      await apiLogout()
    } catch {
      // Session is being discarded either way; server-side blacklist failure
      // must not trap the user in the app.
    } finally {
      get().clearSession()
    }
  },

  bootstrap: async () => {
    try {
      const { access } = await apiRefresh()
      set({ accessToken: access })
      const user = await apiMe()
      set({ user, status: 'authenticated' })
    } catch {
      get().clearSession()
    }
  },

  setAccessToken: (token) => set({ accessToken: token }),

  clearSession: () => set({ user: null, accessToken: null, status: 'unauthenticated' }),
}))
