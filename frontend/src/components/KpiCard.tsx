export function KpiCard({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="glass min-w-[150px] flex-1 rounded-panel border border-line px-4 py-3">
      <p className="text-xs text-muted">{label}</p>
      <p className="text-xl font-semibold leading-tight">{value}</p>
      {hint && <p className="text-xs text-muted">{hint}</p>}
    </div>
  )
}
