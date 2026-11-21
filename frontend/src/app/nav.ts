import {
  Activity, BarChart3, Camera, ClipboardCheck, Cpu, FlaskConical, LayoutDashboard, MessageSquare,
  ScanLine, Settings, ShieldAlert, Upload, type LucideIcon,
} from 'lucide-react'

export interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  /** phase in which the page is built; items from later phases are shown but disabled */
  phase: number
}

export const BUILT_PHASE = 2

export const NAV_GROUPS: { label: string; items: NavItem[] }[] = [
  {
    label: 'Monitor',
    items: [
      { to: '/app/overview', label: 'Overview', icon: LayoutDashboard, phase: 2 },
      { to: '/app/machines', label: 'Machines', icon: Cpu, phase: 3 },
      { to: '/app/incidents', label: 'Incidents', icon: ShieldAlert, phase: 3 },
      { to: '/app/review', label: 'Review queue', icon: ClipboardCheck, phase: 4 },
    ],
  },
  {
    label: 'Intelligence',
    items: [
      { to: '/app/assistant', label: 'AI Assistant', icon: MessageSquare, phase: 6 },
      { to: '/app/analytics', label: 'Analytics', icon: BarChart3, phase: 6 },
      { to: '/app/results', label: 'Results', icon: FlaskConical, phase: 6 },
    ],
  },
  {
    label: 'Setup',
    items: [
      { to: '/app/uploads', label: 'Data uploads', icon: Upload, phase: 5 },
      { to: '/app/cameras', label: 'Cameras', icon: Camera, phase: 5 },
      { to: '/app/ar', label: 'AR and QR codes', icon: ScanLine, phase: 7 },
    ],
  },
  {
    label: 'Account',
    items: [{ to: '/app/settings', label: 'Settings', icon: Settings, phase: 9 }],
  },
]

export const PAGE_TITLES: Record<string, string> = Object.fromEntries(
  NAV_GROUPS.flatMap((g) => g.items.map((i) => [i.to, i.label])),
)

export const BRAND_ICON = Activity
