import { Link } from 'react-router-dom'

export function NotFound() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 p-6 text-center">
      <h1 className="text-lg font-semibold">Page not found</h1>
      <p className="text-muted">The address does not match any page in GenTwin Vision.</p>
      <Link to="/" className="text-accent underline">Go to the start page</Link>
    </div>
  )
}
