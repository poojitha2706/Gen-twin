import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'
import { CommandPalette } from './CommandPalette'
import { useTwin } from '@/store/twin'

export function Shell() {
  const connection = useTwin((s) => s.connection)
  return (
    <div className="flex h-full">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        {connection === 'offline' && (
          <div role="alert" className="border-b border-line bg-warning/15 px-6 py-2 text-sm">
            You are offline. Live updates have stopped and will resume when the connection returns.
          </div>
        )}
        <main className="relative min-h-0 flex-1 overflow-auto"><Outlet /></main>
      </div>
      <CommandPalette />
    </div>
  )
}
