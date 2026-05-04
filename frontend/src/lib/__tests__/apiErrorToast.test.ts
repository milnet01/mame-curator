import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/api/client'
import { toastApiError } from '../apiErrorToast'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
  },
}))

import { toast } from 'sonner'

beforeEach(() => {
  vi.mocked(toast.error).mockClear()
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
})
