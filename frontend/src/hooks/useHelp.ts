import {
  HelpContentSchema,
  HelpIndexSchema,
  type HelpContent,
  type HelpIndex,
} from '@/api/types'
import { useApiQuery } from './useApi'

export function useHelpIndex() {
  return useApiQuery<HelpIndex>(['help', 'index'], '/api/help/index', HelpIndexSchema)
}

export function useHelpTopic(slug: string | null) {
  return useApiQuery<HelpContent>(
    ['help', 'topic', slug],
    `/api/help/${encodeURIComponent(slug ?? '')}`,
    HelpContentSchema,
    { enabled: slug !== null },
  )
}
