import { useMutation } from '@tanstack/react-query'
import { apiRequest } from '@/api/client'
import {
  ValidateResponseSchema,
  type ValidateRequest,
  type ValidateResponse,
} from '@/api/types'

/**
 * P15 § 5.1 — POST /api/games/validate.
 *
 * Splits cart shortnames into {existing, missing} via O(1) lookup
 * against world.machines on the backend. Called pre-Copy: orphaned
 * items are dropped with a single toast and CopyModal opens with
 * the surviving set.
 */
export function useValidateCart() {
  return useMutation({
    mutationFn: (req: ValidateRequest) =>
      apiRequest<ValidateResponse>('/api/games/validate', ValidateResponseSchema, {
        method: 'POST',
        body: req,
      }),
  })
}
