import { create } from 'zustand'
import { loadService, type ConnectionState, type DataService } from '@/services'
import type { IncidentEvent } from '@/types/event'
import type { Machine } from '@/types/machine'

interface TwinState {
  phase: 'loading' | 'ready' | 'error'
  error: string | null
  isSample: boolean
  machines: Machine[]
  events: IncidentEvent[]
  resetAt: Record<string, number>
  avgResponseSeconds: number
  now: number
  connection: ConnectionState
  selectedId: string | null
  focusId: string | null
  focusTick: number
  showLabels: boolean
  unread: IncidentEvent[]
  service: DataService | null
  start: () => Promise<() => void>
  select: (id: string | null) => void
  focus: (id: string) => void
  resetCamera: () => void
  toggleLabels: () => void
  resetMachine: (id: string) => void
  markRead: () => void
}

export const useTwin = create<TwinState>((set, get) => ({
  phase: 'loading',
  error: null,
  isSample: true,
  machines: [],
  events: [],
  resetAt: {},
  avgResponseSeconds: 0,
  now: Date.now(),
  connection: 'reconnecting',
  selectedId: null,
  focusId: null,
  focusTick: 0,
  showLabels: true,
  unread: [],
  service: null,

  async start() {
    set({ phase: 'loading', error: null })
    let stop = () => {}
    try {
      const service = await loadService()
      const [machines, events, avg] = await Promise.all([
        service.getMachines(),
        service.getEvents(),
        service.getAvgResponseSeconds(),
      ])
      set({
        service,
        isSample: service.isSample,
        machines,
        events,
        avgResponseSeconds: avg,
        phase: 'ready',
        now: Date.now(),
      })
      const unsub = service.subscribe(
        (msg) => {
          if (msg.type === 'event') {
            set((s) => ({
              events: [...s.events, msg.event],
              unread: [msg.event, ...s.unread].slice(0, 20),
              now: Date.now(),
            }))
            const m = get().machines.find((x) => x.id === msg.event.machine_id)
            if (m && (msg.event.decision === 'escalate' || msg.event.event_type === 'safety_violation')) {
              get().focus(m.id)
            }
          } else {
            set((s) => ({ resetAt: { ...s.resetAt, [msg.machine_id]: Date.now() }, now: Date.now() }))
          }
        },
        (connection) => set({ connection }),
      )
      const clock = setInterval(() => set({ now: Date.now() }), 15_000)
      stop = () => {
        unsub()
        clearInterval(clock)
      }
    } catch (e) {
      set({
        phase: 'error',
        error: e instanceof Error ? e.message : 'The factory data could not be loaded.',
      })
    }
    return stop
  },

  select: (id) => set({ selectedId: id }),
  focus: (id) => set((s) => ({ focusId: id, focusTick: s.focusTick + 1 })),
  resetCamera: () => set((s) => ({ focusId: null, focusTick: s.focusTick + 1 })),
  toggleLabels: () => set((s) => ({ showLabels: !s.showLabels })),
  resetMachine: (id) =>
    set((s) => ({ resetAt: { ...s.resetAt, [id]: Date.now() }, now: Date.now() })),
  markRead: () => set({ unread: [] }),
}))
