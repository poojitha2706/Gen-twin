import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BUILT_PHASE, NAV_GROUPS } from './nav'
import { useUi } from '@/store/ui'
import { useTwin } from '@/store/twin'
import { useTheme } from '@/store/theme'

interface Cmd { id: string; label: string; hint: string; run: () => void }

export function CommandPalette() {
  const open = useUi((s) => s.paletteOpen)
  const setOpen = useUi((s) => s.setPalette)
  const machines = useTwin((s) => s.machines)
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [i, setI] = useState(0)
  const input = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        useUi.getState().setPalette(!useUi.getState().paletteOpen)
      }
      if (e.key === 'Escape') useUi.getState().setPalette(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  useEffect(() => {
    if (open) { setQ(''); setI(0); setTimeout(() => input.current?.focus(), 0) }
  }, [open])

  const all = useMemo<Cmd[]>(() => {
    const go = (to: string) => () => navigate(to)
    const pages = NAV_GROUPS.flatMap((g) => g.items)
      .filter((p) => p.phase <= BUILT_PHASE)
      .map((p) => ({ id: p.to, label: p.label, hint: 'Page', run: go(p.to) }))
    const ms = machines.map((m) => ({
      id: m.id, label: `${m.name} (${m.id})`, hint: 'Machine',
      run: () => { navigate('/app/overview'); useTwin.getState().select(m.id); useTwin.getState().focus(m.id) },
    }))
    const actions: Cmd[] = [
      { id: 'theme', label: 'Switch theme', hint: 'Action', run: () => {
        const t = useTheme.getState()
        t.setMode(t.resolved === 'dark' ? 'light' : 'dark')
      } },
    ]
    return [...pages, ...ms, ...actions]
  }, [machines, navigate])

  const list = all.filter((c) => c.label.toLowerCase().includes(q.toLowerCase())).slice(0, 8)
  if (!open) return null
  const choose = (c?: Cmd) => { if (c) { setOpen(false); c.run() } }
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-background/60 pt-[15vh]" onMouseDown={() => setOpen(false)}>
      <div role="dialog" aria-label="Command palette" onMouseDown={(e) => e.stopPropagation()} className="w-[560px] max-w-[92vw] rounded-panel border border-line bg-raised shadow-lg">
        <input
          ref={input}
          value={q}
          onChange={(e) => { setQ(e.target.value); setI(0) }}
          onKeyDown={(e) => {
            if (e.key === 'ArrowDown') { e.preventDefault(); setI((x) => Math.min(x + 1, list.length - 1)) }
            if (e.key === 'ArrowUp') { e.preventDefault(); setI((x) => Math.max(x - 1, 0)) }
            if (e.key === 'Enter') choose(list[i])
          }}
          placeholder="Jump to a page, machine or action"
          aria-label="Search"
          className="h-12 w-full rounded-t-panel border-b border-line bg-transparent px-4 outline-none"
        />
        <ul role="listbox" className="max-h-80 overflow-y-auto p-2">
          {list.length === 0 && <li className="p-3 text-sm text-muted">Nothing matches “{q}”.</li>}
          {list.map((c, n) => (
            <li key={c.id} role="option" aria-selected={n === i}>
              <button onMouseEnter={() => setI(n)} onClick={() => choose(c)} className={`flex w-full items-center justify-between rounded-control px-3 py-2 text-left ${n === i ? 'bg-accent/15' : ''}`}>
                <span>{c.label}</span>
                <span className="text-xs text-muted">{c.hint}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
