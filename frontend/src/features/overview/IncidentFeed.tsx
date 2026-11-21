import { ChevronRight } from 'lucide-react'
import { DecisionBadge, IdChip } from '@/components/Badge'
import { EmptyState } from '@/components/EmptyState'
import { label, timeAgo } from '@/lib/format'
import { useTwin } from '@/store/twin'
import { useUi } from '@/store/ui'

export function IncidentFeed() {
  const events = useTwin((s) => s.events)
  const machines = useTwin((s) => s.machines)
  const now = useTwin((s) => s.now)
  const open = useUi((s) => s.feedOpen)
  const setOpen = useUi((s) => s.setFeedOpen)
  const recent = events.slice(-8).reverse()
  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="glass rounded-panel border border-line px-3 py-2 text-sm">
        Show incident feed
      </button>
    )
  }
  return (
    <section aria-label="Incident feed" className="glass flex max-h-full w-[340px] flex-col rounded-panel border border-line">
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        <h2 className="font-semibold">Latest incidents</h2>
        <button onClick={() => setOpen(false)} aria-label="Hide incident feed" className="rounded-control p-1 hover:bg-line/50">
          <ChevronRight size={16} aria-hidden />
        </button>
      </div>
      {recent.length === 0 ? (
        <EmptyState title="No incidents yet" hint="New detections appear here as they happen." />
      ) : (
        <ul className="divide-y divide-line overflow-y-auto">
          {recent.map((e) => {
            const m = machines.find((x) => x.id === e.machine_id)
            return (
              <li key={e.event_id}>
                <button onClick={() => { useTwin.getState().select(e.machine_id); useTwin.getState().focus(e.machine_id) }} className="w-full space-y-1.5 px-4 py-3 text-left hover:bg-line/30">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-medium">{m?.name ?? e.machine_id} · {label(e.label)}</span>
                    <DecisionBadge decision={e.decision} />
                  </div>
                  <p className="text-sm text-muted">{e.cause}</p>
                  <div className="flex flex-wrap items-center gap-1">
                    {e.cited_incidents.map((id) => <IdChip key={id} id={id} />)}
                    <span className="ml-auto text-xs text-muted">{timeAgo(e.timestamp, now)}</span>
                  </div>
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
