import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import { useAuthStore } from '../stores/auth'
import { TEST_USER, VALID_PASSWORD } from '../test/handlers'
import { LoginPage } from './LoginPage'

function renderLogin() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<div>Dashboard Home</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('LoginPage', () => {
  it('renders username and password fields', () => {
    renderLogin()
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('shows a validation error when fields are empty', async () => {
    const user = userEvent.setup()
    renderLogin()
    await user.click(screen.getByRole('button', { name: /sign in/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Username and password are required',
    )
  })

  it('shows the server error on bad credentials', async () => {
    const user = userEvent.setup()
    renderLogin()
    await user.type(screen.getByLabelText(/username/i), 'admin')
    await user.type(screen.getByLabelText(/password/i), 'not-the-password')
    await user.click(screen.getByRole('button', { name: /sign in/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No active account found with the given credentials',
    )
    expect(useAuthStore.getState().status).toBe('unauthenticated')
  })

  it('authenticates and navigates to the dashboard on success', async () => {
    const user = userEvent.setup()
    renderLogin()
    await user.type(screen.getByLabelText(/username/i), TEST_USER.username)
    await user.type(screen.getByLabelText(/password/i), VALID_PASSWORD)
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    expect(await screen.findByText('Dashboard Home')).toBeInTheDocument()
    const s = useAuthStore.getState()
    expect(s.status).toBe('authenticated')
    expect(s.accessToken).toBe('test-access-token')
    expect(s.user?.badge_number).toBe('EFP-0001')
  })
})
