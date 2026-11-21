import type { IncidentEvent, EventType } from '@/types/event'
import type { HealthPoint, Machine } from '@/types/machine'
import { tierFor } from '@/lib/policy'
import type { User } from '@/types/user'

export const SAMPLE_ORG_ID = 'org-demo'

export const SAMPLE_USER: User = {
  id: 'usr-demo',
  name: 'Asha Rao',
  email: 'asha@sample.example',
  org_id: SAMPLE_ORG_ID,
  org_name: 'Northfield Works (sample)',
  role: 'user',
}

function rng(seed: number) {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const clamp = (v: number) => Math.min(1, Math.max(0, v))

export const SAMPLE_MACHINES: Machine[] = [
  { id: 'M-101', name: 'Feed conveyor', template: 'conveyor', line_id: 'L1', position: { x: -5.5, z: -2.5 }, camera_online: true, health: 0.91 },
  { id: 'M-102', name: 'Stamping press', template: 'press', line_id: 'L1', position: { x: -0.5, z: -3 }, camera_online: true, health: 0.74 },
  { id: 'M-201', name: 'CNC mill A', template: 'cnc', line_id: 'L2', position: { x: 4.5, z: -2.5 }, camera_online: true, health: 0.52 },
  { id: 'M-202', name: 'Welding robot', template: 'robot_arm', line_id: 'L2', position: { x: 7.5, z: 1.5 }, camera_online: true, health: 0.66 },
  { id: 'M-301', name: 'Packing station', template: 'generic', line_id: 'L3', position: { x: -4.5, z: 3.5 }, camera_online: true, health: 0.95 },
  { id: 'M-302', name: 'CNC mill B', template: 'cnc', line_id: 'L3', position: { x: 0.5, z: 3.5 }, camera_online: false, health: 0.8 },
]

const RISK: Record<string, number> = {
  'M-101': 0.25, 'M-102': 0.5, 'M-201': 0.75, 'M-202': 0.55, 'M-301': 0.15, 'M-302': 0.4,
}
const RATE: Record<string, number> = {
  'M-101': 1.2, 'M-102': 2, 'M-201': 3.2, 'M-202': 1.8, 'M-301': 0.6, 'M-302': 1.4,
}
const LABELS: Record<EventType, { label: string; cause: string }[]> = {
  defect: [
    { label: 'scratch', cause: 'Worn tool edge leaving surface marks' },
    { label: 'crazing', cause: 'Thermal stress after uneven cooling' },
    { label: 'inclusion', cause: 'Contaminated feedstock batch' },
  ],
  machine_stopped: [
    { label: 'belt_jam', cause: 'Misaligned guide rail blocking parts' },
    { label: 'overload_trip', cause: 'Bearing wear raising motor load' },
  ],
  safety_violation: [
    { label: 'no_helmet_in_zone', cause: 'Operator entered restricted zone without PPE' },
    { label: 'zone_intrusion', cause: 'Person crossed the restricted-zone boundary' },
  ],
}
const HOUR_WEIGHT = [1, 1, 1, 1, 1, 2, 4, 5, 4, 3, 3, 3, 3, 3, 5, 5, 4, 3, 3, 2, 2, 3, 4, 2]

function makeEvent(
  r: () => number,
  n: number,
  m: Machine,
  ts: number,
  forced?: { type?: EventType; score?: number },
): IncidentEvent {
  const roll = r()
  const type: EventType =
    forced?.type ?? (roll < 0.06 ? 'safety_violation' : roll < 0.24 ? 'machine_stopped' : 'defect')
  const pool = LABELS[type]
  const pick = pool[Math.floor(r() * pool.length)]
  const cv = clamp(0.6 + 0.4 * Math.pow(r(), 0.7))
  const hist = clamp((RISK[m.id] ?? 0.4) + 0.3 * (r() - 0.5))
  const cause = clamp(0.5 + 0.5 * Math.pow(r(), 0.8))
  let score = clamp(0.4 * cv + 0.2 * hist + 0.4 * cause)
  if (r() < 0.15) score *= 0.8
  if (forced?.score !== undefined) score = forced.score
  const cited = Array.from({ length: 1 + Math.floor(r() * 3) }, () =>
    `INC-${String(1 + Math.floor(r() * 400)).padStart(4, '0')}`,
  )
  const id = String(n).padStart(6, '0')
  return {
    event_id: `EVT-${id}`,
    timestamp: new Date(ts).toISOString(),
    org_id: SAMPLE_ORG_ID,
    machine_id: m.id,
    line_id: m.line_id,
    event_type: type,
    level: score < 0.6 ? 'high' : score < 0.8 ? 'medium' : 'weak',
    label: pick.label,
    detector_confidence: cv,
    history_risk: hist,
    cause_confidence: cause,
    decision_score: score,
    cause: pick.cause,
    cited_incidents: [...new Set(cited)],
    decision: tierFor(score),
    frame_ref: `frames/${id}.jpg`,
    clip_path: `clips/${id}.mp4`,
  }
}

export interface SampleData {
  machines: Machine[]
  events: IncidentEvent[]
  avgResponseSeconds: number
}

export function createSample(now: number): SampleData {
  const r = rng(20240611)
  const events: IncidentEvent[] = []
  let n = 1
  const DAY = 86_400_000
  const wsum = HOUR_WEIGHT.reduce((a, b) => a + b, 0)
  for (let d = 42; d >= 1; d--) {
    const dayStart = now - d * DAY
    const weekend = [0, 6].includes(new Date(dayStart).getUTCDay())
    for (const m of SAMPLE_MACHINES) {
      const count = Math.round((RATE[m.id] ?? 1) * (weekend ? 0.6 : 1) * (0.5 + r()))
      for (let i = 0; i < count; i++) {
        let h = 0
        let pickW = r() * wsum
        while (pickW > HOUR_WEIGHT[h]) pickW -= HOUR_WEIGHT[h++]
        events.push(makeEvent(r, n++, m, dayStart + h * 3_600_000 + r() * 3_600_000))
      }
    }
  }
  const recent: [string, number, number, EventType][] = [
    ['M-102', 8, 0.74, 'defect'],
    ['M-201', 3, 0.48, 'machine_stopped'],
    ['M-202', 11, 0.93, 'defect'],
  ]
  for (const [id, minAgo, score, type] of recent) {
    const m = SAMPLE_MACHINES.find((x) => x.id === id)!
    events.push(makeEvent(r, n++, m, now - minAgo * 60_000, { type, score }))
  }
  events.sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp))
  return { machines: SAMPLE_MACHINES, events, avgResponseSeconds: 4.2 }
}

export function createHealth(machineId: string, now: number): HealthPoint[] {
  const m = SAMPLE_MACHINES.find((x) => x.id === machineId)
  const r = rng(machineId.split('').reduce((a, c) => a + c.charCodeAt(0), 7))
  const end = m?.health ?? 0.8
  let v = Math.min(1, end + 0.12)
  const out: HealthPoint[] = []
  for (let d = 42; d >= 0; d--) {
    v = clamp(v + (end - v) * 0.06 + (r() - 0.5) * 0.04)
    out.push({ t: new Date(now - d * 86_400_000).toISOString(), value: v })
  }
  return out
}

/** Used by the sample service to simulate a live feed. */
export function createLiveEvent(seed: number, now: number, counter: number): IncidentEvent {
  const r = rng(seed)
  const eligible = SAMPLE_MACHINES.filter((m) => m.camera_online)
  const m = eligible[Math.floor(r() * eligible.length)]
  return makeEvent(r, counter, m, now)
}
