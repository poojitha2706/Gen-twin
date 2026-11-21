import { Check } from 'lucide-react'
import { FactoryScene } from '@/components/scene/FactoryScene'
import { SampleBadge } from '@/components/Badge'
import { Button } from '@/components/Button'
import { Skeleton } from '@/components/Skeleton'
import { useMachineViews } from '@/hooks/useMachineViews'
import { useTwin } from '@/store/twin'
import { useUi } from '@/store/ui'
import { IncidentFeed } from './IncidentFeed'
import { KpiStrip } from './KpiStrip'
import { Legend } from './Legend'
import { MachineDrawer } from './MachineDrawer'

function Onboarding() {
  const steps = ['Add a machine', 'Upload machine history', 'Connect a camera']
  return (
    <div className="glass absolute left-1/2 top-1/2 w-[360px] -translate-x-1/2 -translate-y-1/2 rounded-panel border border-line p-5">
      <h2 className="text-md font-semibold">Set up your factory</h2>
      <p className="mb-3 text-sm text-muted">Your floor is empty. Three steps bring it to life.</p>
      <ol className="space-y-2">
        {steps.map((s) => (
          <li key={s} className="flex items-center gap-2 text-sm">
            <span className="flex h-5 w-5 items-center justify-center rounded-full border border-line"><Check size={12} className="opacity-0" aria-hidden /></span>
            {s}
          </li>
        ))}
      </ol>
    </div>
  )
}

export function OverviewPage() {
  const phase = useTwin((s) => s.phase)
  const error = useTwin((s) => s.error)
  const sample = useTwin((s) => s.isSample)
  const selectedId = useTwin((s) => s.selectedId)
  const views = useMachineViews()
  const feedOpen = useUi((s) => s.feedOpen)

  if (phase === 'error') {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
        <h2 className="text-lg font-semibold">The factory data could not be loaded</h2>
        <p className="max-w-md text-muted">{error}</p>
        <Button variant="primary" onClick={() => void useTwin.getState().start()}>Retry</Button>
      </div>
    )
  }
  if (phase === 'loading') {
    return (
      <div className="space-y-4 p-6">
        <div className="flex gap-3">{Array.from({ length: 5 }, (_, i) => <Skeleton key={i} className="h-16 flex-1" />)}</div>
        <Skeleton className="h-[60vh]" />
      </div>
    )
  }
  return (
    <div className="absolute inset-0">
      <FactoryScene views={views} />
      <div className="pointer-events-none absolute inset-0 flex flex-col justify-between gap-3 p-4">
        <div className="pointer-events-auto flex items-start gap-3">
          <div className="min-w-0 flex-1"><KpiStrip /></div>
          {sample && <SampleBadge />}
        </div>
        <div className="flex min-h-0 flex-1 justify-end py-3">
          <div className="pointer-events-auto flex max-h-full">
            {selectedId ? <MachineDrawer machineId={selectedId} /> : feedOpen ? <IncidentFeed /> : null}
          </div>
        </div>
        <div className="pointer-events-auto flex items-end justify-between">
          <Legend />
          {!feedOpen && !selectedId && <IncidentFeed />}
        </div>
      </div>
      {views.length === 0 && <Onboarding />}
    </div>
  )
}
