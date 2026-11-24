import { afterEach, describe, expect, it, vi } from 'vitest'
import { eventSchema } from '@/types/event'
import { machineSchema } from '@/types/machine'
import { renderService, toEvent, toMachine } from '@/services/renderService'

const rec = (over: Record<string, unknown> = {}) => ({
  id: 'a1',
  machine_id: 'machine_01',
  defect_class: 'patches',
  confidence: 0.9,
  cause: 'uneven descaling leaving oxide patches',
  cause_confidence: 1,
  action: 'escalated',
  timestamp: '2026-11-21T08:41:13.448375',
  ...over,
})

afterEach(() => vi.unstubAllGlobals())

describe('render service mapping', () => {
  it('maps a backend record to a valid event, adding the UTC offset', () => {
    const e = toEvent(rec(), [rec()])
    expect(eventSchema.safeParse(e).success).toBe(true)
    expect(e.timestamp.endsWith('Z')).toBe(true)
    expect(e.cause).toContain('descaling')
    expect(e.decision).toBe('alert')
  })

  it('maps auto_logged to auto_act and a pending record to a placeholder cause', () => {
    expect(toEvent(rec({ action: 'auto_logged' }), [rec()]).decision).toBe('auto_act')
    const pending = toEvent(rec({ cause: null, cause_confidence: null, action: 'pending' }), [])
    expect(pending.cause).toBe('Analysis pending')
    expect(pending.cause_confidence).toBe(0)
  })

  it('builds valid machines and spreads them over the floor', () => {
    const ms = ['machine_01', 'machine_02', 'machine_03'].map((id, i) =>
      toMachine({ machine_id: id, status: 'anomaly_detected', last_updated: '2026-11-21T08:41:13' }, i, 3, [], Date.now()),
    )
    ms.forEach((m) => expect(machineSchema.safeParse(m).success).toBe(true))
    expect(new Set(ms.map((m) => m.position.x)).size).toBe(3)
  })

  it('loads machines and events from the backend and ignores unready records', async () => {
    const recent = new Date(Date.now() - 2000).toISOString().replace('Z', '')
    const fetchMock = vi.fn(async (url: string) => {
      const body = url.endsWith('/machines')
        ? [{ machine_id: 'machine_01', status: 'anomaly_detected', last_updated: recent }]
        : [rec({ id: 'ok', timestamp: recent }), rec({ id: 'wait', cause: null, cause_confidence: null, action: 'pending', timestamp: recent })]
      return { ok: true, json: async () => body }
    })
    vi.stubGlobal('fetch', fetchMock)
    const machines = await renderService.getMachines()
    const events = await renderService.getEvents()
    expect(machines).toHaveLength(1)
    expect(events.map((e) => e.event_id)).toEqual(['ok'])
  })
})
