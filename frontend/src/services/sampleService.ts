import { createHealth, createLiveEvent, createSample, type SampleData } from '@/sample'
import type { DataService } from './types'

let cache: SampleData | null = null
const data = () => (cache ??= createSample(Date.now()))

export const sampleService: DataService = {
  isSample: true,
  getMachines: async () => data().machines,
  getEvents: async () => data().events,
  getHealth: async (id) => createHealth(id, Date.now()),
  getAvgResponseSeconds: async () => data().avgResponseSeconds,
  subscribe(onMessage, onConnection) {
    onConnection('connected')
    let tick = 0
    let counter = 900_000
    const timer = setInterval(() => {
      tick++
      const evt = createLiveEvent(tick * 7919, Date.now(), counter++)
      onMessage({ type: 'event', event: evt })
      // Clear the status again a little later so the floor keeps changing.
      setTimeout(() => onMessage({ type: 'machine_reset', machine_id: evt.machine_id }), 14_000)
    }, 9_000)
    return () => clearInterval(timer)
  },
}
