import { z } from 'zod'

const schema = z.object({
  VITE_DATA_SOURCE: z.enum(['sample', 'api', 'render']).default('sample'),
  VITE_API_URL: z.string().default('http://localhost:8000'),
  VITE_WS_URL: z.string().default('ws://localhost:8000'),
})

const parsed = schema.parse(import.meta.env)

export const env = {
  dataSource: parsed.VITE_DATA_SOURCE,
  apiUrl: parsed.VITE_API_URL,
  wsUrl: parsed.VITE_WS_URL,
}
