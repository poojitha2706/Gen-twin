import { NavLink } from 'react-router-dom'
import { Activity, PanelLeftClose, PanelLeftOpen } from 'lucide-react'
import { BUILT_PHASE, NAV_GROUPS } from './nav'
import { useUi } from '@/store/ui'
import { useSession } from '@/store/session'
import { useTwin } from '@/store/twin'

export function Sidebar() {
  const collapsed = useUi((s) => s.sidebarCollapsed)
  const toggle = useUi((s) => s.toggleSidebar)
  const user = useSession((s) => s.user)
  const sample = useTwin((s) => s.isSample)
  return (
    <aside className={`flex shrink-0 flex-col border-r border-line bg-surface transition-[width] duration-200 ${collapsed ? 'w-16' : 'w-60'}`}>
      <div className="flex h-14 items-center gap-2 border-b border-line px-4">
        <Activity className="shrink-0 text-accent" size={20} aria-hidden />
        {!collapsed && <span className="font-semibold">GenTwin Vision</span>}
      </div>
      <nav aria-label="Main" className="flex-1 space-y-4 overflow-y-auto p-2">
        {NAV_GROUPS.map((g) => (
          <div key={g.label}>
            {!collapsed && <p className="px-2 pb-1 text-xs text-muted">{g.label}</p>}
            <ul className="space-y-0.5">
              {g.items.map((item) => {
                const Icon = item.icon
                const ready = item.phase <= BUILT_PHASE
                const inner = (active: boolean) => (
                  <>
                    <Icon size={18} className="shrink-0" aria-hidden />
                    {!collapsed && <span className="truncate">{item.label}</span>}
                    {active && <span className="sr-only">(current page)</span>}
                  </>
                )
                return (
                  <li key={item.to}>
                    {ready ? (
                      <NavLink
                        to={item.to}
                        title={collapsed ? item.label : undefined}
                        className={({ isActive }) =>
                          `flex h-9 items-center gap-3 rounded-control px-2.5 text-base transition-colors duration-150 ${
                            isActive ? 'bg-accent/15 font-medium text-accent' : 'text-fg hover:bg-line/50'
                          }`
                        }
                      >
                        {({ isActive }) => inner(isActive)}
                      </NavLink>
                    ) : (
                      <span
                        aria-disabled="true"
                        title={`${item.label} arrives in build phase ${item.phase}`}
                        className="flex h-9 cursor-not-allowed items-center gap-3 rounded-control px-2.5 text-base text-muted/60"
                      >
                        {inner(false)}
                      </span>
                    )}
                  </li>
                )
              })}
            </ul>
          </div>
        ))}
      </nav>
      <div className="space-y-2 border-t border-line p-2">
        {!collapsed && user && (
          <div className="px-2 py-1">
            <p className="truncate text-sm font-medium">{user.name}</p>
            <p className="truncate text-xs text-muted">{user.org_name}</p>
            {sample && <p className="mt-1 text-xs text-muted">Sample data</p>}
          </div>
        )}
        <button
          onClick={toggle}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className="flex h-9 w-full items-center gap-3 rounded-control px-2.5 text-muted hover:bg-line/50"
        >
          {collapsed ? <PanelLeftOpen size={18} aria-hidden /> : <PanelLeftClose size={18} aria-hidden />}
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </aside>
  )
}
