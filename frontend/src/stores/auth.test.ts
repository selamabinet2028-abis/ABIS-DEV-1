import { HttpResponse, http } from 'msw'

import { TEST_USER, VALID_PASSWORD } from '../test/handlers'
import { server } from '../test/server'
import { useAuthStore } from './auth'

describe('auth store', () => {
  it('starts idle with no session', () => {
    const s = useAuthStore.getState()
    expect(s.user).toBeNull()
    expect(s.accessToken).toBeNull()
    expect(s.status).toBe('idle')
  })

  it('login stores access token and user in memory on success', async () => {
    await useAuthStore.getState().login(TEST_USER.username, VALID_PASSWORD)
    const s = useAuthStore.getState()
    expect(s.status).toBe('authenticated')
    expect(s.accessToken).toBe('test-access-token')
    expect(s.user?.username).toBe('admin')
    expect(s.user?.role).toBe('admin')
  })

  it('login failure clears session and rethrows', async () => {
    await expect(useAuthStore.getState().login('admin', 'wrong-password')).rejects.toThrow()
    const s = useAuthStore.getState()
    expect(s.status).toBe('unauthenticated')
    expect(s.accessToken).toBeNull()
    expect(s.user).toBeNull()
  })

  it('logout clears the session even if the server call fails', async () => {
    useAuthStore.setState({
      user: TEST_USER,
      accessToken: 'test-access-token',
      status: 'authenticated',
    })
    server.use(
      http.post('*/api/v1/auth/logout/', () => new HttpResponse(null, { status: 500 })),
    )
    await useAuthStore.getState().logout()
    const s = useAuthStore.getState()
    expect(s.status).toBe('unauthenticated')
    expect(s.accessToken).toBeNull()
    expect(s.user).toBeNull()
  })

  it('bootstrap restores the session from the refresh cookie', async () => {
    await useAuthStore.getState().bootstrap()
    const s = useAuthStore.getState()
    expect(s.status).toBe('authenticated')
    expect(s.accessToken).toBe('refreshed-access-token')
    expect(s.user?.username).toBe('admin')
  })

  it('bootstrap ends unauthenticated when refresh is rejected', async () => {
    server.use(
      http.post('*/api/v1/auth/refresh/', () =>
        HttpResponse.json({ detail: 'Token is invalid or expired' }, { status: 401 }),
      ),
    )
    await useAuthStore.getState().bootstrap()
    expect(useAuthStore.getState().status).toBe('unauthenticated')
  })
})
