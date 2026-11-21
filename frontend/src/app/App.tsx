import { useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { ErrorBoundary } from './ErrorBoundary'
import { NotFound } from './NotFound'
import { RequireRole } from './guards'
import { Shell } from './Shell'
import { OverviewPage } from '@/features/overview/OverviewPage'
import { PreviewPage } from '@/features/auth/PreviewPage'
import { useTwin } from '@/store/twin'
import { watchSystemTheme } from '@/store/theme'
import { bootstrapSession } from '@/store/session'

export function App() {
  useEffect(() => {
    const stopTheme = watchSystemTheme()
    let stopTwin = () => {}
    let cancelled = false
    void bootstrapSession().then(() => useTwin.getState().start()).then((stop) => {
      if (cancelled) stop()
      else stopTwin = stop
    })
    return () => {
      cancelled = true
      stopTheme()
      stopTwin()
    }
  }, [])
  return (
    <ErrorBoundary>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="/" element={<PreviewPage />} />
          <Route element={<RequireRole role="user" />}>
            <Route path="/app" element={<Shell />}>
              <Route index element={<Navigate to="overview" replace />} />
              <Route path="overview" element={<OverviewPage />} />
            </Route>
          </Route>
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  )
}
