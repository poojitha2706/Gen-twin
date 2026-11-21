import { z } from 'zod'

export const userSchema = z.object({
  id: z.string(),
  name: z.string(),
  email: z.string().email(),
  org_id: z.string().nullable(),
  org_name: z.string().nullable(),
  role: z.enum(['user', 'admin']),
})

export type User = z.infer<typeof userSchema>
