import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { HealthPoint } from '@/types/machine'

export function TrendChart({ data, label }: { data: HealthPoint[]; label: string }) {
  const rows = data.map((p) => ({ day: p.t.slice(5, 10), value: Math.round(p.value * 100) }))
  const last = rows[rows.length - 1]?.value
  return (
    <figure aria-label={label} className="m-0">
      <ResponsiveContainer width="100%" height={110}>
        <LineChart data={rows} margin={{ top: 6, right: 4, bottom: 0, left: -24 }}>
          <XAxis dataKey="day" tick={{ fontSize: 11, fill: 'rgb(var(--text-muted))' }} interval={13} stroke="rgb(var(--border))" />
          <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: 'rgb(var(--text-muted))' }} stroke="rgb(var(--border))" />
          <Tooltip
            contentStyle={{ background: 'rgb(var(--surface))', border: '1px solid rgb(var(--border))', fontSize: 12 }}
            formatter={(v) => [`${v}%`, 'Health']}
          />
          <Line dataKey="value" stroke="rgb(var(--accent))" strokeWidth={2} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
      <figcaption className="sr-only">{label}. Latest value {last}%.</figcaption>
    </figure>
  )
}
