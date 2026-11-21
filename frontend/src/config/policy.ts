/** The only place decision thresholds are defined. */
export const POLICY = { autoAct: 0.9, alert: 0.6 } as const

export const TIER_COPY = {
  auto_act: {
    label: 'Auto-act',
    rule: 'Score 0.90 or higher',
    detail: 'Logged, machine paused in simulation, ticket created automatically.',
  },
  alert: {
    label: 'Alert',
    rule: 'Score 0.60 to 0.90',
    detail: 'A person is notified with the suggested cause and can review it.',
  },
  escalate: {
    label: 'Escalate',
    rule: 'Score below 0.60',
    detail: 'Sent to the human review queue.',
  },
} as const
