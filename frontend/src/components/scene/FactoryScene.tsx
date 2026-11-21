import { Suspense, useEffect, useMemo, useRef, useState } from 'react'
import { Canvas, useFrame, useThree, type ThreeEvent } from '@react-three/fiber'
import { Billboard, Html, MeshReflectorMaterial, OrbitControls, Sparkles } from '@react-three/drei'
import * as THREE from 'three'
import { Holo } from './Holo'
import { MachineBody } from './Machines'
import { prefersReducedMotion, usePalette, type Palette } from './palette'
import { RESTRICTED_ZONE } from '@/config/scene'
import { useTwin } from '@/store/twin'
import { STATUS_META } from '@/config/status'
import type { MachineView } from '@/lib/status'

const HOME_POS = new THREE.Vector3(12, 8.5, 14)
const HOME_TARGET = new THREE.Vector3(0.5, 0.6, 0)
const PULSE: Record<string, number> = { warning: 3, critical: 7 }
const SPEED: Record<string, number> = { ok: 1, warning: 1, critical: 1.6, paused: 0, offline: 0 }

interface Controls {
  target: THREE.Vector3
  update: () => void
}

function CameraRig() {
  const tick = useTwin((s) => s.focusTick)
  const camera = useThree((s) => s.camera)
  const controls = useThree((s) => s.controls) as unknown as Controls | null
  const goal = useRef<{ t: THREE.Vector3; p: THREE.Vector3 } | null>(null)

  useEffect(() => {
    const { focusId, machines } = useTwin.getState()
    const m = machines.find((x) => x.id === focusId)
    goal.current = m
      ? {
          t: new THREE.Vector3(m.position.x, 1, m.position.z),
          p: new THREE.Vector3(m.position.x + 4.5, 4.5, m.position.z + 6.5),
        }
      : { t: HOME_TARGET.clone(), p: HOME_POS.clone() }
  }, [tick])

  useFrame(() => {
    const g = goal.current
    if (!g || !controls) return
    const k = prefersReducedMotion() ? 1 : 0.07
    controls.target.lerp(g.t, k)
    camera.position.lerp(g.p, k)
    controls.update()
    if (camera.position.distanceTo(g.p) < 0.05) goal.current = null
  })
  return null
}

function Floor({ pal }: { pal: Palette }) {
  const grid = useMemo(() => {
    const g = new THREE.GridHelper(44, 44, pal.grid, pal.grid)
    const m = g.material as THREE.LineBasicMaterial
    m.transparent = true
    m.opacity = pal.dark ? 0.16 : 0.22
    m.depthWrite = false
    return g
  }, [pal])
  return (
    <>
      <mesh rotation-x={-Math.PI / 2}>
        <planeGeometry args={[70, 70]} />
        <MeshReflectorMaterial
          blur={[300, 90]}
          resolution={512}
          mixBlur={1}
          mixStrength={pal.dark ? 28 : 5}
          roughness={0.85}
          depthScale={1}
          minDepthThreshold={0.4}
          maxDepthThreshold={1.4}
          color={pal.floor}
          metalness={0.6}
          mirror={0}
        />
      </mesh>
      <primitive object={grid} position-y={0.02} />
    </>
  )
}

/** The raised catwalk, overhead beams and wall panels that give the hall its depth. */
function Hall({ pal }: { pal: Palette }) {
  const c = pal.holo
  const d = pal.dark
  return (
    <group>
      <Holo shape={{ k: 'box', s: [36, 0.18, 3] }} pos={[0, 3.4, -13]} color={c} dark={d} fill={0.05} line={0.5} />
      <Holo shape={{ k: 'box', s: [36, 0.06, 0.06] }} pos={[0, 4.5, -11.6]} color={c} dark={d} line={0.7} />
      {Array.from({ length: 13 }, (_, i) => (
        <Holo key={i} shape={{ k: 'box', s: [0.06, 1.1, 0.06] }} pos={[-18 + i * 3, 3.95, -11.6]} color={c} dark={d} line={0.5} />
      ))}
      {[-6, 0, 6].map((z) => (
        <Holo key={z} shape={{ k: 'box', s: [36, 0.3, 0.3] }} pos={[0, 8, z - 4]} color={c} dark={d} fill={0.03} line={0.3} />
      ))}
      {[-12, -4, 4, 12].map((x) => (
        <Holo key={x} shape={{ k: 'box', s: [3.4, 2.4, 0.05] }} pos={[x, 6.2, -14.4]} color={x % 8 ? pal.hot : c} dark={d} fill={0.05} line={0.55} />
      ))}
    </group>
  )
}

function HudRing({ pos, r, pal, flip }: { pos: [number, number, number]; r: number; pal: Palette; flip?: boolean }) {
  const arc = useRef<THREE.Mesh>(null)
  const inner = useRef<THREE.Mesh>(null)
  useFrame((_, dt) => {
    if (prefersReducedMotion()) return
    if (arc.current) arc.current.rotation.z -= dt * (flip ? -0.6 : 0.6)
    if (inner.current) inner.current.rotation.z += dt * 0.9
  })
  const mat = (c: THREE.Color, o: number) => (
    <meshBasicMaterial color={c} transparent opacity={o} side={THREE.DoubleSide} depthWrite={false} blending={pal.dark ? THREE.AdditiveBlending : THREE.NormalBlending} />
  )
  return (
    <Billboard position={pos}>
      <mesh>
        <ringGeometry args={[r, r * 1.03, 64]} />
        {mat(pal.holo, 0.8)}
      </mesh>
      <mesh ref={arc}>
        <ringGeometry args={[r * 0.86, r * 0.93, 48, 1, 0, Math.PI * 1.3]} />
        {mat(pal.hot, 0.9)}
      </mesh>
      <mesh ref={inner}>
        <ringGeometry args={[r * 0.6, r * 0.63, 40, 1, 0, Math.PI * 1.6]} />
        {mat(pal.holo, 0.7)}
      </mesh>
    </Billboard>
  )
}

function Zone({ pal, intruder }: { pal: Palette; intruder: boolean }) {
  const mat = useRef<THREE.MeshBasicMaterial>(null)
  useFrame(({ clock }) => {
    if (mat.current) mat.current.opacity = 0.14 + (intruder && !prefersReducedMotion() ? 0.1 * Math.sin(clock.elapsedTime * 7) : 0)
  })
  const { x, z, w, d } = RESTRICTED_ZONE
  const red = pal.status.critical
  return (
    <group position={[x, 0.03, z]}>
      <mesh rotation-x={-Math.PI / 2}>
        <planeGeometry args={[w, d]} />
        <meshBasicMaterial ref={mat} color={red} transparent opacity={0.14} depthWrite={false} />
      </mesh>
      <Holo shape={{ k: 'box', s: [w, 0.04, d] }} color={red} dark={pal.dark} fill={0} line={0.8} />
      {intruder && (
        <group position={[0, 0.9, 0]}>
          <Holo shape={{ k: 'cyl', r: 0.22, h: 1.1, seg: 10 }} color={red} dark={pal.dark} fill={0.2} />
          <Holo shape={{ k: 'torus', r: 0.16, t: 0.08, rad: 6, seg: 10 }} pos={[0, 0.8, 0]} rot={[Math.PI / 2, 0, 0]} color={red} dark={pal.dark} fill={0.3} />
        </group>
      )}
    </group>
  )
}

interface MachineProps {
  view: MachineView
  pal: Palette
  selected: boolean
  interactive: boolean
  labels: boolean
}

function MachineNode({ view, pal, selected, interactive, labels }: MachineProps) {
  const { machine: m, status } = view
  const ring = useRef<THREE.Mesh>(null)
  const [hover, setHover] = useState(false)
  const color = pal.status[status]
  const rate = PULSE[status] ?? 0
  useFrame(({ clock }) => {
    if (!ring.current) return
    const s = rate && !prefersReducedMotion() ? 1 + 0.07 * Math.sin(clock.elapsedTime * rate) : 1
    ring.current.scale.set(s, s, 1)
  })
  const onClick = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation()
    useTwin.getState().select(m.id)
  }
  return (
    <group
      position={[m.position.x, 0, m.position.z]}
      onClick={interactive ? onClick : undefined}
      onPointerOver={interactive ? (e) => { e.stopPropagation(); setHover(true); document.body.style.cursor = 'pointer' } : undefined}
      onPointerOut={interactive ? () => { setHover(false); document.body.style.cursor = '' } : undefined}
    >
      <mesh position={[0, 1.2, 0]}>
        <boxGeometry args={[3.6, 2.6, 2.2]} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} />
      </mesh>
      <mesh ref={ring} rotation-x={-Math.PI / 2} position-y={0.04}>
        <ringGeometry args={[selected || hover ? 2.15 : 2, 2.3, 56]} />
        <meshBasicMaterial color={color} transparent opacity={status === 'offline' ? 0.5 : 0.95} depthWrite={false} side={THREE.DoubleSide} />
      </mesh>
      <mesh rotation-x={-Math.PI / 2} position-y={0.03}>
        <circleGeometry args={[2, 48]} />
        <meshBasicMaterial color={color} transparent opacity={status === 'ok' ? 0.06 : 0.16} depthWrite={false} blending={pal.dark ? THREE.AdditiveBlending : THREE.NormalBlending} />
      </mesh>
      <MachineBody template={m.template} status={status} pal={pal} speed={SPEED[status]} />
      {labels && (
        <Html position={[0, 3.6, 0]} center distanceFactor={16} zIndexRange={[10, 0]}>
          <div className="scene-label" style={selected ? { borderColor: `rgb(var(--accent))` } : undefined}>
            <span className="mono-id text-muted">{m.id}</span> {m.name} · {STATUS_META[status].label}
          </div>
        </Html>
      )}
    </group>
  )
}

interface Props {
  views: MachineView[]
  interactive?: boolean
  autoRotate?: boolean
}

export function FactoryScene({ views, interactive = true, autoRotate = false }: Props) {
  const pal = usePalette()
  const selectedId = useTwin((s) => s.selectedId)
  const labels = useTwin((s) => s.showLabels)
  const intruder = views.some((v) => v.active?.event_type === 'safety_violation')
  const reduced = prefersReducedMotion()
  return (
    <Canvas
      dpr={[1, 1.5]}
      camera={{ position: HOME_POS.toArray(), fov: 42, near: 0.1, far: 120 }}
      gl={{ antialias: true, powerPreference: 'high-performance' }}
      onPointerMissed={() => interactive && useTwin.getState().select(null)}
      aria-label="3D view of the factory floor"
    >
      <color attach="background" args={[pal.bg]} />
      <fog attach="fog" args={[pal.bg, 22, 52]} />
      <hemisphereLight args={[pal.holo, pal.floor, pal.dark ? 0.55 : 1.1]} />
      <pointLight position={[-7, 6, 4]} color={pal.holo} intensity={pal.dark ? 140 : 40} decay={2} />
      <pointLight position={[8, 4, -4]} color={pal.hot} intensity={pal.dark ? 90 : 20} decay={2} />
      <Suspense fallback={null}>
        <Floor pal={pal} />
        <Hall pal={pal} />
        <Zone pal={pal} intruder={intruder} />
        <HudRing pos={[-9.5, 4.6, -6]} r={1.7} pal={pal} />
        <HudRing pos={[-11, 2.6, -2]} r={0.8} pal={pal} flip />
        <HudRing pos={[11, 4.2, -6]} r={1.3} pal={pal} flip />
        {views.map((v) => (
          <MachineNode key={v.machine.id} view={v} pal={pal} selected={v.machine.id === selectedId} interactive={interactive} labels={labels} />
        ))}
        {!reduced && <Sparkles count={90} scale={[26, 7, 18]} size={2} speed={0.25} opacity={pal.dark ? 0.7 : 0.35} color={pal.holo} position={[0, 3.5, 0]} />}
      </Suspense>
      <CameraRig />
      <OrbitControls
        makeDefault
        enableDamping
        enablePan={false}
        target={HOME_TARGET}
        minDistance={5}
        maxDistance={32}
        maxPolarAngle={Math.PI / 2.15}
        minPolarAngle={0.35}
        autoRotate={autoRotate && !reduced}
        autoRotateSpeed={0.35}
      />
    </Canvas>
  )
}
