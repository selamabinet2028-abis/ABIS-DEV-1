import '@testing-library/jest-dom'

import { useAuthStore } from './stores/auth'
import { useToastStore } from './stores/toast'
import { server } from './test/server'

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))

afterEach(() => {
  server.resetHandlers()
  useAuthStore.setState({ user: null, accessToken: null, status: 'idle' })
  useToastStore.setState({ toasts: [] })
})

afterAll(() => server.close())
