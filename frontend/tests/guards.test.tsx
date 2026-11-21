import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { RequireRole, homeFor } from '@/app/guards'
import { useSession } from '@/store/session'
import type { User } from '@/types/user'

const user = (role: User['role']): User => ({ id: '1', name: 'T', email: 't@x.io', org_id: 'o', org_name: 'O', role })

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path="/" element={<p>public</p>} />
        <Route element={<RequireRole role="user" />}><Route path="/app" element={<p>user area</p>} /></Route>
        <Route path="/admin/overview" element={<p>admin home</p>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('route guards', () => {
  it('sends logged-out visitors to the public page', () => {
    useSession.setState({ user: null })
    renderAt('/app')
    expect(screen.getByText('public')).toBeTruthy()
  })
  it('sends admins away from user pages to their own home', () => {
    useSession.setState({ user: user('admin') })
    renderAt('/app')
    expect(screen.getByText('admin home')).toBeTruthy()
    expect(homeFor(user('admin'))).toBe('/admin/overview')
  })
  it('lets users in', () => {
    useSession.setState({ user: user('user') })
    renderAt('/app')
    expect(screen.getByText('user area')).toBeTruthy()
  })
})
