import { SetupCheckSchema, type SetupCheck } from '@/api/types'
import { useApiQuery } from './useApi'

/**
 * GET /api/setup/check — surfaces whether config + paths + reference INI
 * files are present. Drives the Setup banner in Settings so users can
 * see at a glance whether they need to run `mame-curator refresh-inis`
 * (FP16 § C).
 */
export function useSetupCheck() {
  return useApiQuery<SetupCheck>(['setup', 'check'], '/api/setup/check', SetupCheckSchema)
}
