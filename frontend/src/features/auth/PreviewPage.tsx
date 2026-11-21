import { Link } from 'react-router-dom'
import { FactoryScene } from '@/components/scene/FactoryScene'
import { SampleBadge } from '@/components/Badge'
import { useMachineViews } from '@/hooks/useMachineViews'
import { useTwin } from '@/store/twin'
import { useSession } from '@/store/session'
import { homeFor } from '@/app/guards'

export function PreviewPage() {
  const views = useMachineViews()
  const phase = useTwin((s) => s.phase)
  const user = useSession((s) => s.user)
  return (
    <div className="relative h-full">
      {phase === 'ready' && <FactoryScene views={views} interactive={false} autoRotate />}
      <div className="pointer-events-none absolute inset-0 flex flex-col justify-between p-6">
        <div className="flex items-center gap-2">
          <span className="glass pointer-events-auto rounded-full border border-line px-3 py-1 text-sm">Sample factory</span>
          <SampleBadge />
        </div>
        <div className="glass pointer-events-auto max-w-md rounded-panel border border-line p-6">
          <h1 className="text-xl font-semibold">GenTwin Vision</h1>
          <p className="mt-1 text-muted">A live 3D twin of your factory that sees problems, explains the likely cause, and decides when a person should step in.</p>
          <div className="mt-4 flex gap-2">
            <Link to={homeFor(user)} className="inline-flex h-9 items-center rounded-control bg-accent px-4 font-medium text-background hover:opacity-90">
              Open the sample workspace
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
