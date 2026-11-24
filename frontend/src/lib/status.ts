import { ACTIVE_WINDOW_MIN, type MachineStatus } from '@/config/status'
import type { IncidentEvent } from '@/types/event'
import type { Machine } from '@/types/machine'

type Latest = Pick<IncidentEvent, 'decision' | 'event_type'>

export function statusFor(latest: Latest | null, cameraOnline: boolean | null): MachineStatus {
  if (cameraOnline !== true) return 'offline'
  if (!latest) return 'ok'
  if (latest.event_type === 'safety_violation' || latest.decision === 'escalate') return 'critical'
  if (latest.decision === 'auto_act') return 'paused'
  return 'warning'
}

export function activeEvent(
  machineId: string,
  events: IncidentEvent[],
  now: number,
  resetAt = 0,
): IncidentEvent | null {
  const from = Math.max(now - ACTIVE_WINDOW_MIN * 60_000, resetAt)
  let best: IncidentEvent | null = null
  for (const e of events) {
    if (e.machine_id !== machineId) continue
    const t = Date.parse(e.timestamp)
    if (t < from || t > now) continue
    if (!best || t > Date.parse(best.timestamp)) best = e
  }
  return best
}

export interface MachineView {
  machine: Machine
  status: MachineStatus
  active: IncidentEvent | null
}

export function buildViews(
  machines: Machine[],
  events: IncidentEvent[],
  now: number,
  resetAt: Record<string, number>,
): MachineView[] {
  return machines.map((machine) => {
    const active = activeEvent(machine.id, events, now, resetAt[machine.id] ?? 0)
    return { machine, active, status: statusFor(active, machine.camera_online) }
  })
}
