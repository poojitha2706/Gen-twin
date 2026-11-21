import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface UiState {
  sidebarCollapsed: boolean
  paletteOpen: boolean
  feedOpen: boolean
  toggleSidebar: () => void
  setPalette: (open: boolean) => void
  setFeedOpen: (open: boolean) => void
}

export const useUi = create<UiState>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      paletteOpen: false,
      feedOpen: true,
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      setPalette: (paletteOpen) => set({ paletteOpen }),
      setFeedOpen: (feedOpen) => set({ feedOpen }),
    }),
    { name: 'gentwin.ui', partialize: (s) => ({ sidebarCollapsed: s.sidebarCollapsed }) },
  ),
)
