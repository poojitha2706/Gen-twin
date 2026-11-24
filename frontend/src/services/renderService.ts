import { env } from '@/config/env'
import { POLICY } from '@/config/policy'
import { eventSchema, type IncidentEvent } from '@/types/event'
import { machineSchema, type HealthPoint, type LiveMessage, type Machine } from '@/types/machine'
import type { ConnectionState, DataService } from './types'

/**
 * Reads the deployed GenTwin backend (/machines, /machines/{id}/history) and maps it to the
 * types this app uses. No login is needed. Live updates come from polling, not a WebSocket.
 */

interface RenderMachine {
  machine_id: string
  status: string
  last_updated: string
}

interface RenderRecord {
  id: string
  machine_id: string
  defect_class: string
  confidence: number
  cause: string | null
  cause_confidence: number | null
  action: string
  timestamp: string
}

const POLL_MS = 3000
const RISK_WINDOW_MS = 10 * 60 * 1000
const RISK_FULL_AT = 10 // detections inside the window that count as risk 1.0
const ANALYSIS_GRACE_MS = 20_000 // show a detection without a cause after this long
const HEALTH_BUCKETS = 12
const HEALTH_STEP_MS = 5 * 60 * 1000

const clamp01 = (n: number) => Math.min(1, Math.max(0, Number.isFinite(n) ? n : 0))

/** The backend sends UTC timestamps without an offset; add one so the schema accepts them. */
const toIso = (ts: string) => (/(Z|[+-]\d\d:\d\d)$/i.test(ts) ? ts : `${ts}Z`)
const ms = (ts: string) => new Date(toIso(ts)).getTime()

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${env.apiUrl}${path}`)
  if (!res.ok) throw new Error(`Backend returned ${res.status} for ${path}`)
  return (await res.json()) as T
}

async function loadAll() {
  const machines = await get<RenderMachine[]>('/machines')
  const histories = await Promise.all(
    machines.map((m) => get<RenderRecord[]>(`/machines/${encodeURIComponent(m.machine_id)}/history`)),
  )
  return { machines, histories }
}

/** Share of the risk limit used by detections in the 10 minutes up to `at`. */
function riskAt(at: number, history: RenderRecord[]): number {
  const n = history.filter((r) => {
    const t = ms(r.timestamp)
    return t <= at && t > at - RISK_WINDOW_MS
  }).length
  return clamp01(n / RISK_FULL_AT)
}

const title = (id: string) => id.replace(/[_-]+/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())

export function toMachine(m: RenderMachine, index: number, total: number, history: RenderRecord[], now: number): Machine {
  const cols = Math.min(4, Math.max(total, 1))
  const rows = Math.ceil(total / cols)
  const col = index % cols
  const row = Math.floor(index / cols)
  return machineSchema.parse({
    id: m.machine_id,
    name: title(m.machine_id),
    template: 'generic',
    line_id: 'line_1',
    position: { x: (col - (cols - 1) / 2) * 4.5, z: (row - (rows - 1) / 2) * 4 },
    camera_online: true,
    health: m.status === 'normal' ? 1 : 1 - riskAt(now, history),
  })
}

export function toEvent(rec: RenderRecord, history: RenderRecord[]): IncidentEvent {
  const confidence = clamp01(rec.confidence)
  const risk = riskAt(ms(rec.timestamp), history)
  const causeConfidence = clamp01(rec.cause_confidence ?? 0)
  // Same weights as the decision policy used by the analysis module.
  const score = clamp01(0.45 * confidence + 0.35 * risk + 0.2 * causeConfidence)

  let decision: IncidentEvent['decision'] = 'alert'
  if (rec.action === 'auto_logged') decision = 'auto_act'
  else if (rec.action === 'escalated') decision = score >= POLICY.alert ? 'alert' : 'escalate'

  return eventSchema.parse({
    event_id: rec.id,
    timestamp: toIso(rec.timestamp),
    org_id: 'demo-org',
    machine_id: rec.machine_id,
    line_id: 'line_1',
    event_type: 'defect',
    level: score < 0.6 ? 'high' : score < 0.8 ? 'medium' : 'weak',
    label: rec.defect_class,
    detector_confidence: confidence,
    history_risk: risk,
    cause_confidence: causeConfidence,
    decision_score: score,
    cause: rec.cause ?? 'Analysis pending',
    cited_incidents: [],
    decision,
    frame_ref: '',
    clip_path: '',
  })
}

/** A detection is shown once its cause is known, or after a short grace period if analysis never arrives. */
const ready = (rec: RenderRecord, now: number) => rec.cause !== null || now - ms(rec.timestamp) > ANALYSIS_GRACE_MS

function buildEvents(histories: RenderRecord[][], now: number, skip?: Set<string>): IncidentEvent[] {
  const out: IncidentEvent[] = []
  for (const history of histories) {
    for (const rec of history) {
      if (skip?.has(rec.id) || !ready(rec, now)) continue
      try {
        out.push(toEvent(rec, history))
      } catch {
        // skip records the schema rejects instead of breaking the whole dashboard
      }
    }
  }
  return out.sort((a, b) => a.timestamp.localeCompare(b.timestamp))
}

const seen = new Set<string>()

export const renderService: DataService = {
  isSample: false,

  async getMachines() {
    const { machines, histories } = await loadAll()
    const now = Date.now()
    return machines
      .map((m, i) => ({ m, h: histories[i] }))
      .sort((a, b) => a.m.machine_id.localeCompare(b.m.machine_id))
      .map(({ m, h }, i, arr) => toMachine(m, i, arr.length, h, now))
  },

  async getEvents() {
    const { histories } = await loadAll()
    const events = buildEvents(histories, Date.now())
    events.forEach((e) => seen.add(e.event_id))
    return events
  },

  async getHealth(machineId: string): Promise<HealthPoint[]> {
    const history = await get<RenderRecord[]>(`/machines/${encodeURIComponent(machineId)}/history`)
    const now = Date.now()
    return Array.from({ length: HEALTH_BUCKETS }, (_, i) => {
      const at = now - (HEALTH_BUCKETS - 1 - i) * HEALTH_STEP_MS
      return { t: new Date(at).toISOString(), value: 1 - riskAt(at, history) }
    })
  },

  // The backend does not record when analysis finished, so there is no real value to show yet.
  async getAvgResponseSeconds() {
    return 0
  },

  subscribe(onMessage: (m: LiveMessage) => void, onConnection: (s: ConnectionState) => void) {
    let stopped = false
    let busy = false
    let failures = 0
    const lastStatus = new Map<string, string>()

    async function poll() {
      if (stopped || busy) return
      busy = true
      try {
        const { machines, histories } = await loadAll()
        if (stopped) return
        failures = 0
        onConnection('connected')

        for (const m of machines) {
          if (lastStatus.get(m.machine_id) === 'anomaly_detected' && m.status === 'normal') {
            onMessage({ type: 'machine_reset', machine_id: m.machine_id })
          }
          lastStatus.set(m.machine_id, m.status)
        }
        for (const e of buildEvents(histories, Date.now(), seen)) {
          seen.add(e.event_id)
          onMessage({ type: 'event', event: e })
        }
      } catch {
        failures += 1
        onConnection(failures >= 3 ? 'offline' : 'reconnecting')
      } finally {
        busy = false
      }
    }

    const timer = setInterval(poll, POLL_MS)
    void poll()
    return () => {
      stopped = true
      clearInterval(timer)
    }
  },
}
