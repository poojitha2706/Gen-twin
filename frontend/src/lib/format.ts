export const pct = (v: number) => `${Math.round(v * 100)}%`
export const score2 = (v: number) => v.toFixed(2)

export function timeAgo(iso: string, now: number): string {
  const s = Math.max(0, Math.round((now - Date.parse(iso)) / 1000))
  if (s < 60) return `${s}s ago`
  if (s < 3600) return `${Math.floor(s / 60)} min ago`
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`
  return `${Math.floor(s / 86400)} d ago`
}

export const label = (snake: string) => snake.replace(/_/g, ' ')
