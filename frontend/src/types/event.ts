import { z } from 'zod'

const score = z.number().min(0).max(1)

export const eventSchema = z.object({
  event_id: z.string(),
  timestamp: z.string().datetime({ offset: true }),
  org_id: z.string(),
  machine_id: z.string(),
  line_id: z.string(),
  event_type: z.enum(['defect', 'machine_stopped', 'safety_violation']),
  level: z.enum(['weak', 'medium', 'high']),
  label: z.string(),
  detector_confidence: score,
  history_risk: score,
  cause_confidence: score,
  decision_score: score,
  cause: z.string(),
  cited_incidents: z.array(z.string()),
  decision: z.enum(['auto_act', 'alert', 'escalate']),
  frame_ref: z.string(),
  clip_path: z.string(),
})

export type IncidentEvent = z.infer<typeof eventSchema>
export type EventType = IncidentEvent['event_type']
export type Decision = IncidentEvent['decision']
