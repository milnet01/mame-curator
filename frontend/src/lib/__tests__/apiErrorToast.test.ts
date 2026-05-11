import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/api/client'
import {
  _resetApiErrorToastDedupForTests,
  toastApiError,
} from '../apiErrorToast'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
  },
}))

import { toast } from 'sonner'

beforeEach(() => {
  vi.mocked(toast.error).mockClear()
  _resetApiErrorToastDedupForTests()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('toastApiError', () => {
  it('uses byCode-friendly copy when ApiError.code is mapped', () => {
    toastApiError(
      new ApiError(
        { code: 'session_name_invalid', detail: 'raw', fields: [] },
        422,
      ),
    )
    expect(vi.mocked(toast.error)).toHaveBeenCalledWith(
      expect.stringContaining('Session names must start'),
    )
  })

  it('falls back to ApiError.detail when code is unmapped', () => {
    toastApiError(
      new ApiError(
        { code: 'unmapped_test_code', detail: 'detail-text', fields: [] },
        500,
      ),
    )
    expect(vi.mocked(toast.error)).toHaveBeenCalledWith('detail-text')
  })

  it('uses networkTitle + body for ApiError code "network"', () => {
    toastApiError(
      new ApiError(
        { code: 'network', detail: 'fetch failed', fields: [] },
        -1,
      ),
    )
    expect(vi.mocked(toast.error)).toHaveBeenCalledWith(
      expect.stringContaining('Connection problem'),
      expect.objectContaining({ description: expect.any(String) }),
    )
  })

  it('uses genericTitle on non-ApiError throw', () => {
    toastApiError(new Error('boom'))
    expect(vi.mocked(toast.error)).toHaveBeenCalledWith(
      expect.stringContaining('Something went wrong'),
    )
  })

  // FP25-G: cold-start outage burst suppression
  it('FP25-G: dedups identical ApiError bursts within the 1500 ms window', () => {
    const err = new ApiError(
      { code: 'network', detail: 'fetch failed', fields: [] },
      -1,
    )
    // 9-call burst (mimics LibraryPage cold-start fan-out).
    for (let i = 0; i < 9; i++) toastApiError(err)
    expect(vi.mocked(toast.error)).toHaveBeenCalledTimes(1)
  })

  it('FP25-G: re-toasts identical ApiError after the dedup window expires', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-05-11T12:00:00Z'))
    const err = new ApiError(
      { code: 'session_name_invalid', detail: 'raw', fields: [] },
      422,
    )
    toastApiError(err)
    expect(vi.mocked(toast.error)).toHaveBeenCalledTimes(1)

    // Advance > 1500 ms — the next call must toast again.
    vi.setSystemTime(new Date('2026-05-11T12:00:02Z'))
    toastApiError(err)
    expect(vi.mocked(toast.error)).toHaveBeenCalledTimes(2)
  })

  it('FP25-G: distinct (code, detail) pairs are NOT collapsed', () => {
    toastApiError(
      new ApiError(
        { code: 'session_name_invalid', detail: 'raw-1', fields: [] },
        422,
      ),
    )
    toastApiError(
      new ApiError(
        { code: 'override_not_found', detail: 'raw-2', fields: [] },
        404,
      ),
    )
    // Two different (code, detail) keys → two toasts.
    expect(vi.mocked(toast.error)).toHaveBeenCalledTimes(2)
  })

  it('FP25-G: non-ApiError generic burst collapses to one toast', () => {
    for (let i = 0; i < 5; i++) toastApiError(new Error(`boom-${i}`))
    expect(vi.mocked(toast.error)).toHaveBeenCalledTimes(1)
  })
})
