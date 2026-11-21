import { z } from 'zod'
import { env } from '@/config/env'
import { eventSchema } from '@/types/event'
import { machineSchema } from '@/types/machine'
import type { HealthPoint, LiveMessage } from '@/types/machine'
import { useSession } from '@/store/session'
import type { ConnectionState, DataService } from './types'

async function get<T>(path: string, schema: z.ZodType<T>): Promise<T> {
  const token = useSession.getState().token
  const res = await fetch(`${env.apiUrl}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (res.status === 401) {
    useSession.getState().expire()
    throw new Error('Your session expired. Sign in again.')
  }
  if (!res.ok) throw new Error(`The server answered ${res.status} for ${path}.`)
  const parsed = schema.safeParse(await res.json())
  if (!parsed.success) {
    console.error(`Invalid response from ${path}`, parsed.error.flatten())
    throw new Error(`The server sent data for ${path} that does not match the expected format.`)
  }
  return parsed.data
}

const healthSchema = z.array(z.object({ t: z.string(), value: z.number() }))
const messageSchema = z.discriminatedUnion('type', [
  z.object({ type: z.literal('event'), event: eventSchema }),
  z.object({ type: z.literal('machine_reset'), machine_id: z.string() }),
])

export const apiService: DataService = {
  isSample: false,
  getMachines: () => get('/machines', z.array(machineSchema)),
  getEvents: () => get('/events', z.array(eventSchema)),
  getHealth: (id): Promise<HealthPoint[]> => get(`/machines/${id}/health`, healthSchema),
  getAvgResponseSeconds: async () =>
    (await get('/metrics/overview', z.object({ avg_response_seconds: z.number() })))
      .avg_response_seconds,
  subscribe(onMessage, onConnection) {
    let ws: WebSocket | null = null
    let closed = false
    let attempt = 0
    const open = () => {
      const { token, user } = useSession.getState()
      if (!token || !user?.org_id) return onConnection('offline')
      ws = new WebSocket(`${env.wsUrl}/ws/${user.org_id}?token=${encodeURIComponent(token)}`)
      ws.onopen = () => {
        attempt = 0
        onConnection('connected')
      }
      ws.onmessage = (e) => {
        const parsed = messageSchema.safeParse(JSON.parse(String(e.data)))
        if (parsed.success) onMessage(parsed.data as LiveMessage)
        else console.error('Ignored invalid live message', parsed.error.flatten())
      }
      ws.onclose = () => {
        if (closed) return
        const state: ConnectionState = attempt < 5 ? 'reconnecting' : 'offline'
        onConnection(state)
        setTimeout(open, Math.min(30_000, 1000 * 2 ** attempt++))
      }
    }
    open()
    return () => {
      closed = true
      ws?.close()
    }
  },
}
