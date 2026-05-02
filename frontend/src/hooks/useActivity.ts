import {
  ActivityPageSchema,
  type ActivityPage as ActivityPageT,
} from '@/api/types'
import { useApiQuery } from './useApi'

export function useActivity(page: number, pageSize: number) {
  const qs = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  }).toString()
  return useApiQuery<ActivityPageT>(
    ['activity', page, pageSize],
    `/api/activity?${qs}`,
    ActivityPageSchema,
  )
}
