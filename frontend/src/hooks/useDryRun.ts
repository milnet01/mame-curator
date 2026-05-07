import { useMutation } from '@tanstack/react-query'
import { apiRequest } from '@/api/client'
import {
  DryRunReportSchema,
  type CopyJobRequest,
  type DryRunReport,
} from '@/api/types'

/**
 * FP23 — POST /api/copy/dry-run mutation.
 *
 * The backend (``api/routes/copy.py:49``) takes a ``CopyJobRequest``
 * (``selected_names`` + conflict strategy + per-name append decisions)
 * and returns a ``DryRunReport`` with counts (selected / bios /
 * missing_source / already_copied / new) and summary (dest_writable /
 * free_space_gap_bytes / existing_playlist).
 *
 * In FP23 the ``selected_names`` set is the current filter result (the
 * cards visible in ``LibraryPage``). P15 swaps the input source from
 * ``cards`` to ``cart.items`` — the modal contract is unchanged so this
 * hook keeps working as-is once cart input lands.
 */
export function useDryRun() {
  return useMutation({
    mutationFn: (req: CopyJobRequest) =>
      apiRequest<DryRunReport>('/api/copy/dry-run', DryRunReportSchema, {
        method: 'POST',
        body: req,
      }),
  })
}
