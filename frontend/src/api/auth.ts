import type { LoginResponse, RefreshResponse, User } from '../types/auth'

import { client } from './client'

export async function apiLogin(username: string, password: string): Promise<LoginResponse> {
  const { data } = await client.post<LoginResponse>('/auth/login/', { username, password })
  return data
}

export async function apiRefresh(): Promise<RefreshResponse> {
  const { data } = await client.post<RefreshResponse>('/auth/refresh/', {})
  return data
}

export async function apiLogout(): Promise<void> {
  await client.post('/auth/logout/', {})
}

export async function apiMe(): Promise<User> {
  const { data } = await client.get<User>('/users/me/')
  return data
}
