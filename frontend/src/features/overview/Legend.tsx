import { Camera, Tag } from 'lucide-react'
import { STATUS_META, type MachineStatus } from '@/config/status'
import { Button } from '@/components/Button'
import { useTwin } from '@/store/twin'

const COLOR: Record<MachineStatus, string> = {
  ok: 'bg-ok', warning: 'bg-warning', critical: 'bg-critical', paused: 'bg-paused', offline: 'bg-paused',
}

export function Legend() {
  const toggle = useTwin((s) => s.toggleLabels)
  const reset = useTwin((s) => s.resetCamera)
  const labels = useTwin((s) => s.showLabels)
  return (
    <div className="flex items-end gap-3">
      <div className="glass rounded-panel border border-line px-3 py-2">
        <ul className="flex gap-4 text-xs">
          {(Object.keys(STATUS_META) as MachineStatus[]).map((s) => (
            <li key={s} className="flex items-center gap-1.5">
              <span className={`h-2.5 w-2.5 rounded-full ${COLOR[s]} ${s === 'offline' ? 'hatched' : ''}`} aria-hidden />
              {STATUS_META[s].label}
            </li>
          ))}
        </ul>
      </div>
      <div className="glass flex gap-1 rounded-panel border border-line p-1">
        <Button size="sm" variant="ghost" onClick={reset}><Camera size={14} aria-hidden /> Reset camera</Button>
        <Button size="sm" variant="ghost" onClick={toggle} aria-pressed={labels}><Tag size={14} aria-hidden /> Labels {labels ? 'on' : 'off'}</Button>
      </div>
    </div>
  )
}
