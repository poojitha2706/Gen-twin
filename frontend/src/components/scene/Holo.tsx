import { useMemo, useRef, type ReactNode } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

export type Shape =
  | { k: 'box'; s: [number, number, number] }
  | { k: 'cyl'; r: number; h: number; seg?: number }
  | { k: 'torus'; r: number; t: number; rad?: number; seg?: number }

function geometryOf(s: Shape): THREE.BufferGeometry {
  if (s.k === 'box') return new THREE.BoxGeometry(...s.s)
  if (s.k === 'cyl') return new THREE.CylinderGeometry(s.r, s.r, s.h, s.seg ?? 20)
  return new THREE.TorusGeometry(s.r, s.t, s.rad ?? 6, s.seg ?? 24)
}

// Materials are shared by colour so the scene stays cheap.
const lineCache = new Map<string, THREE.LineBasicMaterial>()
const faceCache = new Map<string, THREE.MeshBasicMaterial>()

function lineMat(color: THREE.Color, additive: boolean, opacity: number) {
  const key = `${color.getHexString()}${additive}${opacity}`
  let m = lineCache.get(key)
  if (!m) {
    m = new THREE.LineBasicMaterial({
      color,
      transparent: true,
      opacity,
      blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending,
      depthWrite: false,
    })
    lineCache.set(key, m)
  }
  return m
}

function faceMat(color: THREE.Color, additive: boolean, opacity: number) {
  const key = `${color.getHexString()}${additive}${opacity}`
  let m = faceCache.get(key)
  if (!m) {
    m = new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity,
      blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending,
      depthWrite: false,
      side: THREE.DoubleSide,
    })
    faceCache.set(key, m)
  }
  return m
}

interface HoloProps {
  shape: Shape
  pos?: [number, number, number]
  rot?: [number, number, number]
  color: THREE.Color
  dark: boolean
  fill?: number
  line?: number
  spin?: { axis: 'x' | 'y' | 'z'; speed: number }
  children?: ReactNode
}

/** A primitive drawn as glowing edges over a faint translucent body. */
export function Holo({
  shape, pos = [0, 0, 0], rot = [0, 0, 0], color, dark, fill = 0.07, line = 0.95, spin, children,
}: HoloProps) {
  const geo = useMemo(() => geometryOf(shape), [shape])
  const edges = useMemo(() => new THREE.EdgesGeometry(geo, 25), [geo])
  const ref = useRef<THREE.Group>(null)
  useFrame((_, dt) => {
    if (spin && ref.current) ref.current.rotation[spin.axis] += dt * spin.speed
  })
  return (
    <group position={pos} rotation={rot}>
      <group ref={ref}>
        <mesh geometry={geo} material={faceMat(color, dark, fill)} />
        <lineSegments geometry={edges} material={lineMat(color, dark, line)} />
      </group>
      {children}
    </group>
  )
}
