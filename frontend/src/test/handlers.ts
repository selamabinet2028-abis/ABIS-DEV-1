import { HttpResponse, http } from 'msw'

import type { User } from '../types/auth'

export const TEST_USER: User = {
  id: '7a9d2f7e-1111-4222-8333-444455556666',
  username: 'admin',
  first_name: 'Abebe',
  last_name: 'Kebede',
  email: 'admin@efpc.gov.et',
  role: 'admin',
  org_unit: 'Headquarters',
  badge_number: 'EFP-0001',
}

export const VALID_PASSWORD = 'Admin@12345'

export const handlers = [
  http.post('*/api/v1/auth/login/', async ({ request }) => {
    const body = (await request.json()) as { username?: string; password?: string }
    if (body.username === TEST_USER.username && body.password === VALID_PASSWORD) {
      return HttpResponse.json({ access: 'test-access-token', user: TEST_USER })
    }
    return HttpResponse.json(
      { detail: 'No active account found with the given credentials' },
      { status: 401 },
    )
  }),

  http.post('*/api/v1/auth/refresh/', () =>
    HttpResponse.json({ access: 'refreshed-access-token' }),
  ),

  http.post('*/api/v1/auth/logout/', () => new HttpResponse(null, { status: 205 })),

  http.get('*/api/v1/users/me/', () => HttpResponse.json(TEST_USER)),
]
