import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type Mode = 'light' | 'dark' | 'system'
export type Accent = 'blue' | 'teal' | 'violet' | 'amber'
export const ACCENTS: Accent[] = ['blue', 'teal', 'violet', 'amber']

export function resolveMode(mode: Mode): 'light' | 'dark' {
  if (mode !== 'system') return mode
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

interface ThemeState {
  mode: Mode
  accent: Accent
  resolved: 'light' | 'dark'
  setMode: (m: Mode) => void
  setAccent: (a: Accent) => void
}

function apply(mode: Mode, accent: Accent) {
  const resolved = resolveMode(mode)
  document.documentElement.dataset.theme = resolved
  document.documentElement.dataset.accent = accent
  return resolved
}

export const useTheme = create<ThemeState>()(
  persist(
    (set, get) => ({
      mode: 'system',
      accent: 'blue',
      resolved: 'dark',
      setMode: (mode) => set({ mode, resolved: apply(mode, get().accent) }),
      setAccent: (accent) => set({ accent, resolved: apply(get().mode, accent) }),
    }),
    {
      name: 'gentwin.theme',
      partialize: (s) => ({ mode: s.mode, accent: s.accent }),
      onRehydrateStorage: () => (s) => {
        if (s) useTheme.setState({ resolved: apply(s.mode, s.accent) })
      },
    },
  ),
)

export function watchSystemTheme() {
  const q = window.matchMedia?.('(prefers-color-scheme: dark)')
  const handler = () => {
    const { mode, accent } = useTheme.getState()
    if (mode === 'system') useTheme.setState({ resolved: apply(mode, accent) })
  }
  q?.addEventListener('change', handler)
  return () => q?.removeEventListener('change', handler)
}
