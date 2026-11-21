import { POLICY, TIER_COPY } from '@/config/policy'
import { score2 } from '@/lib/format'
import type { IncidentEvent } from '@/types/event'

function Bar({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm">
        <span>{label}</span>
        <span className="font-medium">{score2(value)}</span>
      </div>
      <div className="h-2 rounded-full bg-line/70">
        <div className="h-2 rounded-full bg-accent" style={{ width: `${value * 100}%` }} />
      </div>
    </div>
  )
}

export function DecisionBreakdown({ event }: { event: IncidentEvent }) {
  const s = event.decision_score
  return (
    <div className="space-y-3">
      <Bar label="Camera detector" value={event.detector_confidence} />
      <Bar label="Machine history risk" value={event.history_risk} />
      <Bar label="Retrieval agreement" value={event.cause_confidence} />
      <div className="pt-1">
        <div className="mb-1 flex justify-between text-sm">
          <span className="font-medium">Decision score</span>
          <span className="font-medium">{score2(s)}</span>
        </div>
        <div className="relative h-3 rounded-full bg-line/70" role="img" aria-label={`Decision score ${score2(s)}, tier ${TIER_COPY[event.decision].label}`}>
          <div className="absolute inset-y-0 left-0 rounded-l-full bg-fg/25" style={{ width: `${s * 100}%` }} />
          {[POLICY.alert, POLICY.autoAct].map((t) => (
            <div key={t} className="absolute -top-1 h-5 w-px bg-muted" style={{ left: `${t * 100}%` }} />
          ))}
          <div className="absolute -top-1 h-5 w-1 rounded-full bg-accent" style={{ left: `calc(${s * 100}% - 2px)` }} />
        </div>
        <div className="relative mt-1 h-4 text-xs text-muted">
          <span className="absolute -translate-x-1/2" style={{ left: `${POLICY.alert * 100}%` }}>{POLICY.alert.toFixed(2)}</span>
          <span className="absolute -translate-x-1/2" style={{ left: `${POLICY.autoAct * 100}%` }}>{POLICY.autoAct.toFixed(2)}</span>
        </div>
        <p className="mt-1 text-sm text-muted">
          Tier: {TIER_COPY[event.decision].label}. {TIER_COPY[event.decision].detail}
        </p>
        {event.event_type === 'safety_violation' && (
          <p className="mt-1 text-sm text-critical">Safety override: a person is always notified.</p>
        )}
      </div>
    </div>
  )
}
