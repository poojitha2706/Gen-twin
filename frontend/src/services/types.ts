import type { IncidentEvent } from '@/types/event'
import type { HealthPoint, LiveMessage, Machine } from '@/types/machine'

export type ConnectionState = 'connected' | 'reconnecting' | 'offline'

export interface DataService {
  /** True when every value comes from the built-in sample module. */
  readonly isSample: boolean
  getMachines(): Promise<Machine[]>
  getEvents(): Promise<IncidentEvent[]>
  getHealth(machineId: string): Promise<HealthPoint[]>
  getAvgResponseSeconds(): Promise<number>
  subscribe(
    onMessage: (m: LiveMessage) => void,
    onConnection: (s: ConnectionState) => void,
  ): () => void
}
