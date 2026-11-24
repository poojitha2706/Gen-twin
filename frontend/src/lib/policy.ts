import { POLICY } from '@/config/policy'
import type { Decision, EventType } from '@/types/event'

export function tierFor(score: number): Decision {
  if (score >= POLICY.autoAct) return 'auto_act'
  if (score >= POLICY.alert) return 'alert'
  return 'escalate'
}

/** Safety events always notify a human, whatever the score. */
export function notifiesHuman(type: EventType, decision: Decision): boolean {
  return type === 'safety_violation' || decision !== 'auto_act'
}
