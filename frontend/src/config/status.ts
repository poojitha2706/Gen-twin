export const ACTIVE_WINDOW_MIN = 30

export const STATUS_META = {
  ok: { label: 'OK', token: 'status-ok' },
  warning: { label: 'Warning', token: 'status-warning' },
  critical: { label: 'Critical', token: 'status-critical' },
  paused: { label: 'Paused', token: 'status-paused' },
  offline: { label: 'Offline', token: 'status-paused' },
} as const

export type MachineStatus = keyof typeof STATUS_META
