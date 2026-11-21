import { beforeEach, describe, expect, it } from 'vitest'
import { useTheme } from '@/store/theme'

describe('theme', () => {
  beforeEach(() => {
    localStorage.clear()
  })
  it('applies mode and accent to the document and persists them', () => {
    useTheme.getState().setMode('light')
    useTheme.getState().setAccent('teal')
    expect(document.documentElement.dataset.theme).toBe('light')
    expect(document.documentElement.dataset.accent).toBe('teal')
    const saved = JSON.parse(localStorage.getItem('gentwin.theme') ?? '{}')
    expect(saved.state).toEqual({ mode: 'light', accent: 'teal' })
  })
})
