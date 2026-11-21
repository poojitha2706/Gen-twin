import { Component, type ReactNode } from 'react'
import { Button } from '@/components/Button'

export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() {
    return { failed: true }
  }
  componentDidCatch(error: Error) {
    console.error('Unhandled UI error', error)
  }
  render() {
    if (!this.state.failed) return this.props.children
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
        <h1 className="text-lg font-semibold">This page stopped working</h1>
        <p className="max-w-md text-muted">The error was logged. Reloading usually fixes it. If it keeps happening, tell your administrator what you were doing.</p>
        <Button variant="primary" onClick={() => location.reload()}>Reload</Button>
      </div>
    )
  }
}
