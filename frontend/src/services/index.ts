import { env } from '@/config/env'
import type { DataService } from './types'

/** The one place that decides sample vs api. The sample module is never loaded in api mode. */
export async function loadService(): Promise<DataService> {
  if (env.dataSource === 'sample') return (await import('./sampleService')).sampleService
  return (await import('./apiService')).apiService
}

export type { DataService, ConnectionState } from './types'
