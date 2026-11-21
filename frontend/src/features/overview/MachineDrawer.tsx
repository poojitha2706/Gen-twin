import { useEffect, useState } from 'react'
import { RotateCcw, X } from 'lucide-react'
import { Button } from '@/components/Button'
import { DecisionBadge, IdChip, StatusBadge } from '@/components/Badge'
import { DecisionBreakdown } from '@/components/DecisionBreakdown'
import { Skeleton } from '@/components/Skeleton'
import { TrendChart } from '@/components/TrendChart'
import { label, pct, timeAgo } from '@/lib/format'
import { TEMPLATE_LABEL, type HealthPoint } from '@/types/machine'
import { useMachineViews } from '@/hooks/useMachineViews'
import { useTwin } from '@/store/twin'

export function MachineDrawer({ machineId }: { machineId: string }) {
  const view = useMachineViews().find((v) => v.machine.id === machineId)
  const events = useTwin((s) => s.events)
  const service = useTwin((s) => s.service)
  const now = useTwin((s) => s.now)
  const [health, setHealth] = useState<HealthPoint[] | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let live = true
    setHealth(null)
    setFailed(false)
    service?.getHealth(machineId).then((h) => live && setHealth(h)).catch(() => live && setFailed(true))
    return () => { live = false }
  }, [machineId, service])

  if (!view) return null
  const { machine: m, status, active } = view
  const recent = events.filter((e) => e.machine_id === m.id).slice(-5).reverse()
  const latest = active ?? recent[0]
  return (
    <aside aria-label={`${m.name} details`} className="glass flex max-h-full w-[380px] flex-col rounded-panel border border-line shadow-lg">
      <div className="flex items-start justify-between border-b border-line p-4">
        <div>
          <h2 className="text-md font-semibold">{m.name}</h2>
          <p className="mt-0.5 flex items-center gap-2 text-sm text-muted"><IdChip id={m.id} /> {TEMPLATE_LABEL[m.template]} · Line {m.line_id}</p>
        </div>
        <button onClick={() => useTwin.getState().select(null)} aria-label="Close details" className="rounded-control p-1 hover:bg-line/50"><X size={18} aria-hidden /></button>
      </div>
      <div className="space-y-5 overflow-y-auto p-4">
        <div className="flex items-center justify-between">
          <StatusBadge status={status} />
          <span className="text-sm text-muted">Health <span className="font-semibold text-fg">{pct(m.health)}</span></span>
        </div>
        <section>
          <h3 className="mb-1 text-sm font-medium">Health, last 6 weeks</h3>
          {failed ? <p className="text-sm text-critical">The health history could not be loaded.</p>
            : health ? <TrendChart data={health} label={`Health trend for ${m.name}`} /> : <Skeleton className="h-[110px]" />}
        </section>
        <section>
          <h3 className="mb-2 text-sm font-medium">{active ? 'Active incident' : 'Latest incident'}</h3>
          {latest ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium">{label(latest.label)}</span>
                <DecisionBadge decision={latest.decision} />
              </div>
              <p className="text-sm text-muted">{latest.cause}</p>
              <DecisionBreakdown event={latest} />
            </div>
          ) : <p className="text-sm text-muted">No incidents recorded for this machine.</p>}
        </section>
        <section>
          <h3 className="mb-1 text-sm font-medium">Recent incidents</h3>
          <ul className="divide-y divide-line text-sm">
            {recent.map((e) => (
              <li key={e.event_id} className="flex items-center gap-2 py-2">
                <IdChip id={e.event_id} /><span className="truncate">{label(e.label)}</span>
                <span className="ml-auto text-xs text-muted">{timeAgo(e.timestamp, now)}</span>
              </li>
            ))}
          </ul>
        </section>
        <Button onClick={() => useTwin.getState().resetMachine(m.id)} disabled={!active}>
          <RotateCcw size={16} aria-hidden /> Reset status
        </Button>
      </div>
    </aside>
  )
}
