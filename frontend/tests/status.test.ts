import { describe, expect, it } from 'vitest'
import { activeEvent, statusFor } from '@/lib/status'
import { createSample } from '@/sample'

describe('machine status mapping', () => {
  it('follows the status table', () => {
    expect(statusFor(null, true)).toBe('ok')
    expect(statusFor({ decision: 'alert', event_type: 'defect' }, true)).toBe('warning')
    expect(statusFor({ decision: 'escalate', event_type: 'defect' }, true)).toBe('critical')
    expect(statusFor({ decision: 'alert', event_type: 'safety_violation' }, true)).toBe('critical')
    expect(statusFor({ decision: 'auto_act', event_type: 'defect' }, true)).toBe('paused')
    expect(statusFor(null, false)).toBe('offline')
    expect(statusFor(null, null)).toBe('offline')
  })
  it('ignores events before a reset', () => {
    const now = Date.now()
    const { events } = createSample(now)
    expect(activeEvent('M-201', events, now)).not.toBeNull()
    expect(activeEvent('M-201', events, now, now)).toBeNull()
  })
})
