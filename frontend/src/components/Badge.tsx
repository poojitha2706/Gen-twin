import { CheckCircle2, OctagonAlert, PauseCircle, TriangleAlert, WifiOff } from 'lucide-react'
import { STATUS_META, type MachineStatus } from '@/config/status'
import { TIER_COPY } from '@/config/policy'
import type { Decision } from '@/types/event'

const base = 'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium'

const ICON = {
  ok: CheckCircle2,
  warning: TriangleAlert,
  critical: OctagonAlert,
  paused: PauseCircle,
  offline: WifiOff,
}
const TEXT: Record<MachineStatus, string> = {
  ok: 'text-ok border-ok/40 bg-ok/10',
  warning: 'text-warning border-warning/40 bg-warning/10',
  critical: 'text-critical border-critical/40 bg-critical/10',
  paused: 'text-paused border-paused/40 bg-paused/10',
  offline: 'text-paused border-paused/40 hatched',
}

export function StatusBadge({ status }: { status: MachineStatus }) {
  const Icon = ICON[status]
  return (
    <span className={`${base} ${TEXT[status]}`}>
      <Icon size={12} aria-hidden /> {STATUS_META[status].label}
    </span>
  )
}

const DECISION: Record<Decision, string> = {
  auto_act: 'text-paused border-paused/40',
  alert: 'text-warning border-warning/40',
  escalate: 'text-critical border-critical/40',
}

export function DecisionBadge({ decision }: { decision: Decision }) {
  return <span className={`${base} ${DECISION[decision]}`}>{TIER_COPY[decision].label}</span>
}

export function SampleBadge() {
  return (
    <span className={`${base} border-line text-muted`} title="Values come from built-in sample data">
      Sample data
    </span>
  )
}

export function IdChip({ id }: { id: string }) {
  return (
    <span className="mono-id rounded-control border border-line bg-background px-1.5 py-0.5 text-muted">
      {id}
    </span>
  )
}
