import { createBrowserRouter } from 'react-router-dom'

import { ProtectedRoute } from './auth/ProtectedRoute'
import { AppShell } from './components/layout/AppShell'
import { NAV_ITEMS } from './components/layout/nav'
import { DashboardPage } from './pages/DashboardPage'
import { LoginPage } from './pages/LoginPage'
import { ModulePlaceholderPage } from './pages/ModulePlaceholderPage'
import { NotFoundPage } from './pages/NotFoundPage'

export const routes = [
  { path: '/login', element: <LoginPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppShell />,
        children: [
          { path: '/', element: <DashboardPage /> },
          // Placeholder routes for every nav module until T-018 delivers pages.
          ...NAV_ITEMS.filter((i) => i.to !== '/').map((i) => ({
            path: i.to,
            element: <ModulePlaceholderPage />,
          })),
        ],
      },
    ],
  },
  { path: '*', element: <NotFoundPage /> },
]

export const router = createBrowserRouter(routes)
