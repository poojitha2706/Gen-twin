import { useState } from 'react'
import { useLocation } from 'react-router-dom'
import { Bell, Monitor, Moon, Search, Sun } from 'lucide-react'
import { PAGE_TITLES } from './nav'
import { useUi } from '@/store/ui'
import { useTwin } from '@/store/twin'
import { useTheme } from '@/store/theme'
import { timeAgo } from '@/lib/format'
import { DecisionBadge, IdChip } from '@/components/Badge'

const CONN = {
  connected: { label: 'Connected', dot: 'bg-ok' },
  reconnecting: { label: 'Reconnecting', dot: 'bg-warning' },
  offline: { label: 'Offline', dot: 'bg-paused' },
}

export function TopBar() {
  const { pathname } = useLocation()
  const setPalette = useUi((s) => s.setPalette)
  const connection = useTwin((s) => s.connection)
  const unread = useTwin((s) => s.unread)
  const markRead = useTwin((s) => s.markRead)
  const now = useTwin((s) => s.now)
  const { mode, setMode } = useTheme()
  const [bell, setBell] = useState(false)
  const next = mode === 'system' ? 'dark' : mode === 'dark' ? 'light' : 'system'
  const ModeIcon = mode === 'system' ? Monitor : mode === 'dark' ? Moon : Sun
  const c = CONN[connection]
  return (
    <header className="relative z-20 flex h-14 shrink-0 items-center gap-3 border-b border-line bg-surface px-6">
      <h1 className="text-md font-semibold">{PAGE_TITLES[pathname] ?? 'GenTwin Vision'}</h1>
      <button
        onClick={() => setPalette(true)}
        className="ml-4 flex h-9 w-72 items-center gap-2 rounded-control border border-line bg-background px-3 text-sm text-muted hover:border-muted"
      >
        <Search size={16} aria-hidden /> Search pages, machines, incidents
        <kbd className="ml-auto rounded border border-line px-1 text-xs">Ctrl K</kbd>
      </button>
      <div className="ml-auto flex items-center gap-3">
        <span role="status" className="flex items-center gap-2 text-sm text-muted">
          <span className={`h-2 w-2 rounded-full ${c.dot}`} aria-hidden /> {c.label}
        </span>
        <div className="relative">
          <button
            onClick={() => { setBell((b) => !b); if (bell) markRead() }}
            aria-label={`Notifications, ${unread.length} unread`}
            className="relative flex h-9 w-9 items-center justify-center rounded-control hover:bg-line/50"
          >
            <Bell size={18} aria-hidden />
            {unread.length > 0 && (
              <span className="absolute right-0.5 top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-accent px-1 text-xs font-semibold text-background">
                {unread.length}
              </span>
            )}
          </button>
          {bell && (
            <div className="absolute right-0 top-11 w-80 rounded-panel border border-line bg-raised p-2 shadow-lg">
              {unread.length === 0 ? (
                <p className="p-3 text-sm text-muted">No new incidents since you last looked.</p>
              ) : (
                <ul>
                  {unread.slice(0, 6).map((e) => (
                    <li key={e.event_id} className="flex items-center gap-2 rounded-control p-2 text-sm">
                      <IdChip id={e.machine_id} />
                      <span className="truncate">{e.label.replace(/_/g, ' ')}</span>
                      <span className="ml-auto"><DecisionBadge decision={e.decision} /></span>
                      <span className="sr-only">{timeAgo(e.timestamp, now)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
        <button
          onClick={() => setMode(next)}
          aria-label={`Theme: ${mode}. Switch to ${next}`}
          title={`Theme: ${mode}`}
          className="flex h-9 w-9 items-center justify-center rounded-control hover:bg-line/50"
        >
          <ModeIcon size={18} aria-hidden />
        </button>
      </div>
    </header>
  )
}
