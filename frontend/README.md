# GenTwin Vision (frontend)

Real-time smart factory monitoring with a live 3D digital twin. Phase 1 (foundation) plus the
Overview and public preview screens, so the 3D floor can be seen and judged early.

## Run

```bash
npm install
npm run dev        # http://localhost:5173, runs on built-in sample data, no backend needed
```

| Script | What it does |
| --- | --- |
| `npm run dev` | Dev server |
| `npm run lint` | ESLint, zero warnings allowed |
| `npm run typecheck` | TypeScript strict check |
| `npm test` | Vitest, report written to `outputs/` (git-ignored) |
| `npm run build` | Type-check and production build |

## Environment

Copy `.env.example` to `.env`. `VITE_DATA_SOURCE=sample` (default) uses `src/sample/`;
`api` talks to the backend at `VITE_API_URL` / `VITE_WS_URL`. In sample mode the demo user is
signed in automatically because the sign-in screens arrive in phase 2.

## What exists now

- Design tokens, light/dark/system themes and four accents, applied before first paint
- Shared components, app shell (sidebar, top bar, command palette on Ctrl+K), route guards, error boundary, not-found page
- Services layer with the sample/api switch, Zod-validated API client and WebSocket with backoff
- Frozen event schema, decision policy (`src/config/policy.ts`), status mapping
- Public preview and Overview: a holographic 3D factory floor, KPI strip, incident feed, machine drawer with decision breakdown

Sidebar items for later phases are shown disabled with a tooltip naming their phase.

## Folder map

`src/app` shell and routing · `src/config` policy, status, env · `src/types` Zod schemas ·
`src/styles` tokens · `src/lib` pure logic · `src/hooks` · `src/components` shared UI and the 3D scene ·
`src/features` per-screen code · `src/services` the only backend access · `src/store` Zustand ·
`src/sample` the one sample-data module · `tests` automated tests · `docs` contract and architecture.

## Honesty note

Incident records are synthetic and the factory is simulated. Everything drawn from sample data
carries a "Sample data" badge.
