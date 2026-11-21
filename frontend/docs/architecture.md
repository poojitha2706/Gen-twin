# Architecture

## Data flow, WebSocket to screen

1. `services/index.ts` picks `sampleService` or `apiService` from `VITE_DATA_SOURCE`.
   The sample module is loaded by dynamic import, so api mode never ships or runs it.
2. `store/twin.ts` calls `service.subscribe`. Each incoming message is validated with Zod
   (api mode) and applied: an `event` is appended, a `machine_reset` records a reset time.
3. `lib/status.ts` derives each machine's status from its newest event inside the active
   window (30 minutes, `config/status.ts`) that is newer than its last reset.
4. `hooks/useMachineViews.ts` exposes those views. The 3D scene, KPI strip, feed and drawer
   all read them, so every surface agrees.
5. A new escalated or safety event calls `focus(machineId)`, which moves the camera.

## Rules enforced by structure

- Only `services/` talks to the backend. Features never import `src/sample/`.
- Thresholds live only in `config/policy.ts`.
- Scene colours come from CSS tokens through `components/scene/palette.ts`.

## Known assumptions

- The old backend adapter (`POST /anomaly`, `new_anomaly` messages) is not built yet because its
  exact payload shapes are not in the brief. Send one sample of each message to finish it.
- "Waiting for review" currently counts non-auto events in the last 24 hours. Phase 4
  subtracts reviewed ones.
