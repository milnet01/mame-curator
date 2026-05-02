import { StatsSchema, type Stats } from '@/api/types'
import { useApiQuery } from './useApi'

export function useStats() {
  return useApiQuery<Stats>(['stats'], '/api/stats', StatsSchema)
}
