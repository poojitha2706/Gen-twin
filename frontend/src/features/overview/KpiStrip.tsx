import { useMemo } from 'react'
import { KpiCard } from '@/components/KpiCard'
import { useMachineViews } from '@/hooks/useMachineViews'
import { useTwin } from '@/store/twin'
import { pct } from '@/lib/format'

const DAY = 86_400_000

export function KpiStrip() {
  const views = useMachineViews()
  const events = useTwin((s) => s.events)
  const now = useTwin((s) => s.now)
  const avg = useTwin((s) => s.avgResponseSeconds)
  const k = useMemo(() => {
    const week = events.filter((e) => Date.parse(e.timestamp) > now - 7 * DAY)
    const day = events.filter((e) => Date.parse(e.timestamp) > now - DAY)
    return {
      running: views.filter((v) => v.status === 'ok' || v.status === 'warning').length,
      open: views.filter((v) => v.active).length,
      auto: week.length ? week.filter((e) => e.decision === 'auto_act').length / week.length : 0,
      waiting: day.filter((e) => e.decision !== 'auto_act').length,
    }
  }, [views, events, now])
  return (
    <div className="flex flex-wrap gap-3">
      <KpiCard label="Machines running" value={`${k.running} of ${views.length}`} />
      <KpiCard label="Open incidents" value={String(k.open)} />
      <KpiCard label="Handled automatically" value={pct(k.auto)} hint="Last 7 days" />
      <KpiCard label="Waiting for review" value={String(k.waiting)} hint="Last 24 hours" />
      <KpiCard label="Average response" value={`${avg.toFixed(1)} s`} />
    </div>
  )
}
