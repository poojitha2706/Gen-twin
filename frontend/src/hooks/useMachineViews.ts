import { useMemo } from 'react'
import { useTwin } from '@/store/twin'
import { buildViews } from '@/lib/status'

export function useMachineViews() {
  const machines = useTwin((s) => s.machines)
  const events = useTwin((s) => s.events)
  const now = useTwin((s) => s.now)
  const resetAt = useTwin((s) => s.resetAt)
  return useMemo(() => buildViews(machines, events, now, resetAt), [machines, events, now, resetAt])
}
