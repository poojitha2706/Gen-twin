import { describe, expect, it } from 'vitest'
import { eventSchema } from '@/types/event'
import { createSample } from '@/sample'

describe('event schema', () => {
  it('accepts every sample event', () => {
    const { events } = createSample(Date.UTC(2026, 9, 27))
    expect(events.length).toBeGreaterThan(200)
    for (const e of events) expect(eventSchema.safeParse(e).success).toBe(true)
  })
  it('rejects scores outside 0 to 1', () => {
    const [e] = createSample(Date.now()).events
    expect(eventSchema.safeParse({ ...e, decision_score: 1.4 }).success).toBe(false)
  })
  it('is deterministic for the same clock', () => {
    const a = createSample(1_000_000_000_000).events.map((e) => e.decision_score)
    const b = createSample(1_000_000_000_000).events.map((e) => e.decision_score)
    expect(a).toEqual(b)
  })
})
