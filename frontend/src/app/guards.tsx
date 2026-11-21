import { Navigate, Outlet } from 'react-router-dom'
import { useSession } from '@/store/session'
import type { User } from '@/types/user'

export const homeFor = (user: User | null) =>
  !user ? '/' : user.role === 'admin' ? '/admin/overview' : '/app/overview'

export function RequireRole({ role }: { role: User['role'] }) {
  const user = useSession((s) => s.user)
  if (!user) return <Navigate to="/" replace />
  if (user.role !== role) return <Navigate to={homeFor(user)} replace />
  return <Outlet />
}
