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
export async function bootstrapSession() {
  if (env.dataSource !== 'sample') return
  const { SAMPLE_USER } = await import('@/sample')
  useSession.getState().signIn(SAMPLE_USER, 'sample-token')
}
