import { describe, expect, it } from 'vitest'
import { notifiesHuman, tierFor } from '@/lib/policy'

describe('decision policy', () => {
  it('maps scores to tiers at the thresholds', () => {
    expect(tierFor(0.95)).toBe('auto_act')
    expect(tierFor(0.9)).toBe('auto_act')
    expect(tierFor(0.89)).toBe('alert')
    expect(tierFor(0.6)).toBe('alert')
    expect(tierFor(0.59)).toBe('escalate')
  })
  it('always notifies a human for safety events', () => {
    expect(notifiesHuman('safety_violation', 'auto_act')).toBe(true)
    expect(notifiesHuman('defect', 'auto_act')).toBe(false)
    expect(notifiesHuman('defect', 'alert')).toBe(true)
  })
})
