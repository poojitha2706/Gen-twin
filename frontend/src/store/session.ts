import { create } from 'zustand'
import { env } from '@/config/env'
import type { User } from '@/types/user'

interface SessionState {
  user: User | null
  token: string | null
  expired: boolean
  signIn: (user: User, token: string) => void
  signOut: () => void
  expire: () => void
}

export const useSession = create<SessionState>((set) => ({
  user: null,
  token: null,
  expired: false,
  signIn: (user, token) => set({ user, token, expired: false }),
  signOut: () => set({ user: null, token: null }),
  expire: () => set({ user: null, token: null, expired: true }),
}))

/** Sample mode has no backend, so the demo user is signed in from the start. */
const DEMO_USER: User = {
  id: 'demo',
  name: 'Demo operator',
  email: 'operator@gentwin.local',
  org_id: 'demo-org',
  org_name: 'GenTwin demo',
  role: 'user',
}

export async function bootstrapSession() {
  if (env.dataSource === 'api') return
  if (env.dataSource === 'render') {
    // The deployed backend has no login, so the demo operator is signed in from the start.
    useSession.getState().signIn(DEMO_USER, 'demo-token')
    return
  }
  const { SAMPLE_USER } = await import('@/sample')
  useSession.getState().signIn(SAMPLE_USER, 'sample-token')
}
