import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { Holo, type Shape } from './Holo'
import type { Palette } from './palette'
import type { MachineStatus } from '@/config/status'
import type { Template } from '@/types/machine'

interface Props {
  template: Template
  status: MachineStatus
  pal: Palette
  /** 0 stops motion */
  speed: number
}

const box = (x: number, y: number, z: number): Shape => ({ k: 'box', s: [x, y, z] })

export function MachineBody({ template, status, pal, speed }: Props) {
  const body = status === 'offline' ? pal.status.offline : pal.holo
  // The component that matters most (gear, piston, joint) takes the status colour when
  // something is wrong, which is where an AR hotspot would later point.
  const heart =
    status === 'ok' ? pal.holoBright : status === 'offline' ? pal.status.offline : pal.status[status]
  const d = pal.dark
  const heartFill = status === 'ok' ? 0.12 : 0.28
  switch (template) {
    case 'conveyor':
      return <Conveyor body={body} heart={heart} d={d} speed={speed} heartFill={heartFill} />
    case 'press':
      return <Press body={body} heart={heart} d={d} speed={speed} heartFill={heartFill} />
    case 'cnc':
      return <Cnc body={body} heart={heart} d={d} speed={speed} heartFill={heartFill} />
    case 'robot_arm':
      return <Robot body={body} heart={heart} d={d} speed={speed} heartFill={heartFill} />
    default:
      return <Generic body={body} heart={heart} d={d} speed={speed} heartFill={heartFill} />
  }
}

interface P {
  body: THREE.Color
  heart: THREE.Color
  d: boolean
  speed: number
  heartFill: number
}

function Conveyor({ body, heart, d, speed, heartFill }: P) {
  const items = useRef<THREE.Group>(null)
  useFrame(({ clock }) => {
    items.current?.children.forEach((c, i) => {
      c.position.x = ((clock.elapsedTime * speed * 0.5 + i / 3) % 1) * 3 - 1.5
    })
  })
  return (
    <group>
      <Holo shape={box(3.4, 0.35, 1)} pos={[0, 0.55, 0]} color={body} dark={d} />
      <Holo shape={box(0.15, 0.4, 0.9)} pos={[-1.4, 0.2, 0]} color={body} dark={d} />
      <Holo shape={box(0.15, 0.4, 0.9)} pos={[1.4, 0.2, 0]} color={body} dark={d} />
      <Holo shape={box(3.4, 0.1, 0.08)} pos={[0, 0.8, 0.5]} color={body} dark={d} />
      <Holo shape={box(3.4, 0.1, 0.08)} pos={[0, 0.8, -0.5]} color={body} dark={d} />
      <Holo shape={{ k: 'cyl', r: 0.3, h: 0.9, seg: 14 }} pos={[-1.7, 0.6, 0]} rot={[Math.PI / 2, 0, 0]} color={heart} dark={d} fill={heartFill} spin={{ axis: 'y', speed: speed * 2 }} />
      <group ref={items} position={[0, 1.05, 0]}>
        {[0, 1, 2].map((i) => (
          <Holo key={i} shape={box(0.42, 0.3, 0.42)} color={body} dark={d} fill={0.14} />
        ))}
      </group>
    </group>
  )
}

function Press({ body, heart, d, speed, heartFill }: P) {
  const piston = useRef<THREE.Group>(null)
  useFrame(({ clock }) => {
    if (piston.current) piston.current.position.y = 1.9 + Math.sin(clock.elapsedTime * 2.2 * speed) * 0.35 * (speed ? 1 : 0)
  })
  return (
    <group>
      <Holo shape={box(2.2, 0.3, 1.6)} pos={[0, 0.15, 0]} color={body} dark={d} />
      <Holo shape={box(1.2, 0.2, 0.9)} pos={[0, 0.4, 0]} color={body} dark={d} />
      <Holo shape={box(0.25, 2.3, 0.25)} pos={[-0.9, 1.35, 0]} color={body} dark={d} />
      <Holo shape={box(0.25, 2.3, 0.25)} pos={[0.9, 1.35, 0]} color={body} dark={d} />
      <Holo shape={box(2.2, 0.4, 1)} pos={[0, 2.7, 0]} color={body} dark={d} />
      <group ref={piston} position={[0, 1.9, 0]}>
        <Holo shape={{ k: 'cyl', r: 0.22, h: 1.1, seg: 14 }} color={heart} dark={d} fill={heartFill} />
        <Holo shape={box(0.9, 0.2, 0.7)} pos={[0, -0.6, 0]} color={heart} dark={d} fill={heartFill} />
      </group>
    </group>
  )
}

function Cnc({ body, heart, d, speed, heartFill }: P) {
  return (
    <group>
      <Holo shape={box(2.6, 1.9, 1.8)} pos={[0, 0.95, 0]} color={body} dark={d} />
      <Holo shape={box(1.1, 1.2, 0.06)} pos={[0.55, 1.1, 0.92]} color={body} dark={d} fill={0.14} />
      <Holo shape={box(0.5, 0.9, 0.06)} pos={[-1.0, 1.0, 0.92]} color={body} dark={d} />
      <Holo shape={{ k: 'cyl', r: 0.28, h: 0.8, seg: 12 }} pos={[0.55, 2.3, 0]} color={body} dark={d} />
      {/* the big gear, front and centre */}
      <Holo shape={{ k: 'torus', r: 0.68, t: 0.14, rad: 6, seg: 18 }} pos={[-0.55, 1.15, 1.0]} color={heart} dark={d} fill={heartFill} spin={{ axis: 'z', speed: speed * 0.9 }}>
        <Holo shape={{ k: 'cyl', r: 0.3, h: 0.18, seg: 12 }} rot={[Math.PI / 2, 0, 0]} color={heart} dark={d} fill={heartFill} />
      </Holo>
    </group>
  )
}

function Robot({ body, heart, d, speed, heartFill }: P) {
  const lower = useRef<THREE.Group>(null)
  const upper = useRef<THREE.Group>(null)
  useFrame(({ clock }) => {
    const t = clock.elapsedTime * speed
    if (lower.current) lower.current.rotation.z = Math.sin(t * 0.8) * 0.35 * (speed ? 1 : 0) - 0.15
    if (upper.current) upper.current.rotation.z = 0.9 + Math.sin(t * 1.2) * 0.3 * (speed ? 1 : 0)
  })
  return (
    <group>
      <Holo shape={{ k: 'cyl', r: 0.7, h: 0.3, seg: 18 }} pos={[0, 0.15, 0]} color={body} dark={d} />
      <Holo shape={{ k: 'cyl', r: 0.35, h: 0.6, seg: 14 }} pos={[0, 0.6, 0]} color={body} dark={d} />
      <group ref={lower} position={[0, 0.95, 0]}>
        <Holo shape={box(0.24, 1.4, 0.24)} pos={[0, 0.7, 0]} color={body} dark={d} />
        <group ref={upper} position={[0, 1.4, 0]}>
          <Holo shape={{ k: 'cyl', r: 0.22, h: 0.4, seg: 12 }} rot={[Math.PI / 2, 0, 0]} color={heart} dark={d} fill={heartFill} />
          <Holo shape={box(0.2, 1.2, 0.2)} pos={[0, 0.6, 0]} color={body} dark={d} />
          <Holo shape={box(0.3, 0.2, 0.3)} pos={[0, 1.25, 0]} color={body} dark={d} />
        </group>
      </group>
    </group>
  )
}

function Generic({ body, heart, d, speed, heartFill }: P) {
  return (
    <group>
      <Holo shape={box(1.9, 1.2, 1.4)} pos={[0, 0.6, 0]} color={body} dark={d} />
      <Holo shape={box(0.9, 0.5, 0.06)} pos={[0, 0.75, 0.72]} color={body} dark={d} fill={0.14} />
      <Holo shape={{ k: 'cyl', r: 0.3, h: 0.35, seg: 12 }} pos={[0.45, 1.4, 0]} color={heart} dark={d} fill={heartFill} spin={{ axis: 'y', speed: speed * 1.5 }} />
    </group>
  )
}
