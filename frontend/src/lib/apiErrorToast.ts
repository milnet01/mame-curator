import { toast } from 'sonner'

import { ApiError } from '@/api/client'
import { strings } from '@/strings'

/**
 * Render a thrown error from a react-query mutation as a user-visible toast.
 * FP13 § A wires every project mutation through this so 422/404/500/network
 * failures stop being silent. ApiError → byCode lookup → detail fallback;
 * code === 'network' uses the connection-problem strings; non-ApiError →
 * generic.
 */
export function toastApiError(err: unknown): void {
  if (err instanceof ApiError) {
    if (err.code === 'network') {
      toast.error(strings.errors.networkTitle, {
        description: strings.errors.networkBody,
      })
      return
    }
    const friendly =
      strings.errors.byCode[err.code as keyof typeof strings.errors.byCode]
    toast.error(friendly ?? err.detail)
    return
  }
  toast.error(strings.errors.genericTitle)
}
