import { z } from 'zod'
import type { IncidentEvent } from './event'

export const templateSchema = z.enum(['conveyor', 'press', 'cnc', 'robot_arm', 'generic'])

export const machineSchema = z.object({
  id: z.string(),
  name: z.string(),
  template: templateSchema,
  line_id: z.string(),
  position: z.object({ x: z.number(), z: z.number() }),
  /** null means no camera is registered */
  camera_online: z.boolean().nullable(),
  health: z.number().min(0).max(1),
})

export type Machine = z.infer<typeof machineSchema>
export type Template = z.infer<typeof templateSchema>

export const TEMPLATE_LABEL: Record<Template, string> = {
  conveyor: 'Conveyor',
  press: 'Press',
  cnc: 'CNC',
  robot_arm: 'Robot arm',
  generic: 'Generic',
}

export interface HealthPoint {
  t: string
  value: number
}

export type LiveMessage =
  | { type: 'event'; event: IncidentEvent }
  | { type: 'machine_reset'; machine_id: string }
