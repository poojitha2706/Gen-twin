import { useMemo } from 'react'
import * as THREE from 'three'
import { useTheme } from '@/store/theme'
import type { MachineStatus } from '@/config/status'

function token(name: string): THREE.Color {
  const raw = getComputedStyle(document.documentElement).getPropertyValue(`--${name}`).trim()
  const [r, g, b] = raw.split(/\s+/).map(Number)
  return new THREE.Color().setRGB(r / 255, g / 255, b / 255, THREE.SRGBColorSpace)
}

export interface Palette {
  dark: boolean
  bg: THREE.Color
  floor: THREE.Color
  grid: THREE.Color
  holo: THREE.Color
  holoBright: THREE.Color
  hot: THREE.Color
  accent: THREE.Color
  status: Record<MachineStatus, THREE.Color>
}

/** Scene colours follow the active theme. Status colours come from the CSS tokens. */
export function usePalette(): Palette {
  const resolved = useTheme((s) => s.resolved)
  const accent = useTheme((s) => s.accent)
  return useMemo(() => {
    const dark = resolved === 'dark'
    const c = (hex: string) => new THREE.Color(hex)
    return {
      dark,
      bg: token('background'),
      floor: c(dark ? '#05090c' : '#d9e1e4'),
      grid: c(dark ? '#2fb8d8' : '#3d7f92'),
      holo: c(dark ? '#3fd0f2' : '#0d7894'),
      holoBright: c(dark ? '#b8f3ff' : '#0a5a70'),
      hot: c(dark ? '#ff8a2b' : '#c2570c'),
      accent: token('accent'),
      status: {
        ok: token('status-ok'),
        warning: token('status-warning'),
        critical: token('status-critical'),
        paused: token('status-paused'),
        offline: token('status-paused'),
      },
    }
    // accent is read so the palette refreshes when it changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resolved, accent])
}

export const prefersReducedMotion = () =>
  typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches
