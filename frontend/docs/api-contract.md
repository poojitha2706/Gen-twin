# API contract the frontend expects

All responses are validated with Zod. `org_id` is derived from the token and never sent by the client.

- Auth: `POST /auth/signup`, `POST /auth/login`, `GET /auth/me`
- Machines: `GET /machines`, `POST /machines`, `GET /machines/{id}`, `PATCH /machines/{id}`,
  `DELETE /machines/{id}`, `GET /machines/{id}/health`, `POST /machines/{id}/reset`
- Cameras: `GET /cameras`, `POST /cameras`, `PATCH /cameras/{id}`
- Events: `GET /events` (filters, sorting, pagination), `GET /events/{id}`, `POST /events/{id}/review`
- Evidence: `GET /clips/{event_id}`, `GET /snapshots/{event_id}` (authenticated, organisation checked)
- Uploads: `POST /uploads/history`, `POST /uploads/history/{id}/mapping`, `POST /uploads/documents`, `GET /uploads`
- Chat: `POST /chat` (streaming; text, citations, optional commands such as `focus_machine`)
- Metrics: `GET /metrics/overview` (`avg_response_seconds`), `GET /metrics/timeseries`, `GET /results`
- Organisation: `GET /org/usage`
- Admin: `GET /admin/overview|organisations|users|logins|usage|health|audit`, `GET`/`POST /billing/plan`
- WebSocket: `/ws/{org_id}?token=...` sending `event`, `machine_state`, `review_update`, `notification`

Used by phase 1: `GET /machines`, `GET /events`, `GET /machines/{id}/health`,
`GET /metrics/overview`, and the WebSocket `event` and `machine_reset` messages.

Event shape: see `src/types/event.ts`.
