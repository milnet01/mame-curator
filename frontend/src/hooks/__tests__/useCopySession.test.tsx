import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'

import { server, http, HttpResponse } from '@/test/handlers'
import { makeClientWrapper } from '@/test/renderWithClient'
import { useCopySession } from '../useCopySession'

// ---------------------------------------------------------------------------
// MockEventSource — jsdom has no native EventSource
// ---------------------------------------------------------------------------

class MockEventSource {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSED = 2
  static instances: MockEventSource[] = []
  url: string
  onmessage: ((ev: MessageEvent) => void) | null = null
  onerror: ((ev: Event) => void) | null = null
  closed = false
  readyState = MockEventSource.OPEN

  constructor(url: string) {
    this.url = url
    MockEventSource.instances.push(this)
  }

  emit(data: unknown) {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }))
  }

  // Helpers for FP24-I (transient drop) and FP24-K (parse error).
  emitRaw(raw: string) {
    this.onmessage?.(new MessageEvent('message', { data: raw }))
  }
  emitTransientError() {
    // Browser EventSource keeps readyState at CONNECTING during retry.
    this.readyState = MockEventSource.CONNECTING
    this.onerror?.(new Event('error'))
  }
  emitTerminalError() {
    this.readyState = MockEventSource.CLOSED
    this.onerror?.(new Event('error'))
  }

  close() {
    this.closed = true
    this.readyState = MockEventSource.CLOSED
  }
}

// ---------------------------------------------------------------------------
// Test setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.stubGlobal('EventSource', MockEventSource)
  MockEventSource.instances = []

  server.use(
    http.post('/api/copy/start', () => HttpResponse.json({ job_id: 'job-123' })),
    http.post('/api/copy/pause', () =>
      HttpResponse.json({
        job_id: 'job-123',
        state: 'paused',
        started_at: '2026-05-07T20:00:00Z',
        files_done: 0,
        files_total: 1,
        bytes_done: 0,
        bytes_total: 1024,
      }),
    ),
    http.post('/api/copy/resume', () =>
      HttpResponse.json({
        job_id: 'job-123',
        state: 'running',
        started_at: '2026-05-07T20:00:00Z',
        files_done: 0,
        files_total: 1,
        bytes_done: 0,
        bytes_total: 1024,
      }),
    ),
    http.post('/api/copy/abort', () =>
      HttpResponse.json({
        job_id: 'job-123',
        state: 'aborted',
        started_at: '2026-05-07T20:00:00Z',
        files_done: 0,
        files_total: 1,
        bytes_done: 0,
        bytes_total: 1024,
      }),
    ),
  )
})

afterEach(() => {
  // FP31: removed redundant explicit `cleanup()` — vitest `globals: true`
  // enables RTL's auto-cleanup. The sibling hook-test files dropped this
  // during DS04 T3.1; useCopySession.test.tsx was missed in that pass.
  vi.unstubAllGlobals()
})

const renderWithClient = makeClientWrapper

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useCopySession', () => {
  it('starts in null state', () => {
    const { result } = renderHook(() => useCopySession(), {
      wrapper: renderWithClient(),
    })
    expect(result.current.state).toBeNull()
  })

  it('after start() + job_started SSE event, state.jobId and state.state populate', async () => {
    const { result } = renderHook(() => useCopySession(), {
      wrapper: renderWithClient(),
    })
    act(() => {
      result.current.start({
        selected_names: ['pacman'],
        conflict_strategy: 'CANCEL',
        append_decisions: {},
      })
    })
    await waitFor(() => expect(MockEventSource.instances).toHaveLength(1))
    act(() => {
      MockEventSource.instances[0].emit({
        event: 'job_started',
        payload: { files_total: 1, bytes_total: 1024 },
        ts: new Date().toISOString(),
      })
    })
    await waitFor(() => {
      expect(result.current.state?.jobId).toBe('job-123')
      expect(result.current.state?.state).toBe('running')
      expect(result.current.state?.filesTotal).toBe(1)
    })
  })

  it('file_started + file_progress events update currentFile and filesDone', async () => {
    const { result } = renderHook(() => useCopySession(), {
      wrapper: renderWithClient(),
    })
    act(() => {
      result.current.start({
        selected_names: ['pacman'],
        conflict_strategy: 'CANCEL',
        append_decisions: {},
      })
    })
    await waitFor(() => expect(MockEventSource.instances).toHaveLength(1))
    act(() => {
      const es = MockEventSource.instances[0]
      es.emit({
        event: 'job_started',
        payload: { files_total: 1, bytes_total: 1024 },
        ts: new Date().toISOString(),
      })
      es.emit({
        event: 'file_started',
        payload: { short_name: 'pacman' },
        ts: new Date().toISOString(),
      })
      es.emit({
        event: 'file_progress',
        payload: { files_done: 1, bytes_done: 1024 },
        ts: new Date().toISOString(),
      })
    })
    await waitFor(() => {
      expect(result.current.state?.filesDone).toBe(1)
      expect(result.current.state?.currentFile).toBe('pacman')
    })
  })

  it('job_finished closes the SSE source and flips state to finished', async () => {
    const { result } = renderHook(() => useCopySession(), {
      wrapper: renderWithClient(),
    })
    act(() => {
      result.current.start({
        selected_names: ['pacman'],
        conflict_strategy: 'CANCEL',
        append_decisions: {},
      })
    })
    await waitFor(() => expect(MockEventSource.instances).toHaveLength(1))
    const es = MockEventSource.instances[0]
    act(() => {
      es.emit({
        event: 'job_finished',
        payload: {},
        ts: new Date().toISOString(),
      })
    })
    await waitFor(() => {
      expect(result.current.state?.state).toBe('finished')
      expect(es.closed).toBe(true)
    })
  })

  it('reset() clears state and closes any open SSE', async () => {
    const { result } = renderHook(() => useCopySession(), {
      wrapper: renderWithClient(),
    })
    act(() => {
      result.current.start({
        selected_names: ['pacman'],
        conflict_strategy: 'CANCEL',
        append_decisions: {},
      })
    })
    await waitFor(() => expect(MockEventSource.instances).toHaveLength(1))
    act(() => result.current.reset())
    expect(result.current.state).toBeNull()
    expect(MockEventSource.instances[0].closed).toBe(true)
  })

  // FP24-H: a second start() call before the first stream terminates
  // must close the orphan stream so it doesn't keep dispatching events
  // into a hook whose state has moved on.
  it('a second start() closes the previous stream', async () => {
    const { result } = renderHook(() => useCopySession(), {
      wrapper: renderWithClient(),
    })
    act(() => {
      result.current.start({
        selected_names: ['a'],
        conflict_strategy: 'CANCEL',
        append_decisions: {},
      })
    })
    await waitFor(() => expect(MockEventSource.instances).toHaveLength(1))
    act(() => {
      result.current.start({
        selected_names: ['b'],
        conflict_strategy: 'CANCEL',
        append_decisions: {},
      })
    })
    await waitFor(() => expect(MockEventSource.instances).toHaveLength(2))
    expect(MockEventSource.instances[0].closed).toBe(true)
  })

  // FP24-I: onerror with a transient (CONNECTING) readyState means the
  // browser is auto-reconnecting; we must not unconditionally close.
  it('transient SSE error does NOT close the stream', async () => {
    const { result } = renderHook(() => useCopySession(), {
      wrapper: renderWithClient(),
    })
    act(() => {
      result.current.start({
        selected_names: ['pacman'],
        conflict_strategy: 'CANCEL',
        append_decisions: {},
      })
    })
    await waitFor(() => expect(MockEventSource.instances).toHaveLength(1))
    const es = MockEventSource.instances[0]
    act(() => es.emitTransientError())
    expect(es.closed).toBe(false)
  })

  it('terminal SSE error (readyState=CLOSED) closes the stream', async () => {
    const { result } = renderHook(() => useCopySession(), {
      wrapper: renderWithClient(),
    })
    act(() => {
      result.current.start({
        selected_names: ['pacman'],
        conflict_strategy: 'CANCEL',
        append_decisions: {},
      })
    })
    await waitFor(() => expect(MockEventSource.instances).toHaveLength(1))
    const es = MockEventSource.instances[0]
    act(() => es.emitTerminalError())
    expect(es.closed).toBe(true)
  })

  // FP24-K: malformed SSE data must not crash the hook.
  it('malformed SSE payload is logged and discarded, hook state intact', async () => {
    const consoleWarn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    try {
      const { result } = renderHook(() => useCopySession(), {
        wrapper: renderWithClient(),
      })
      act(() => {
        result.current.start({
          selected_names: ['pacman'],
          conflict_strategy: 'CANCEL',
          append_decisions: {},
        })
      })
      await waitFor(() => expect(MockEventSource.instances).toHaveLength(1))
      const es = MockEventSource.instances[0]
      // FP31: emit job_started first so `state.state === 'running'` is
      // the established precondition, not an implicit side effect of
      // `start()`. The malformed-payload contract is then unambiguous:
      // a bad message after a real running state must not flip state to
      // null / 'idle' / 'errored'.
      act(() =>
        es.emit({
          event: 'job_started',
          payload: {
            job_id: 'j1',
            files_total: 1,
            bytes_total: 1024,
            started_at: new Date().toISOString(),
          },
          ts: new Date().toISOString(),
        }),
      )
      await waitFor(() => expect(result.current.state?.state).toBe('running'))
      // Send raw garbage that JSON.parse throws on
      act(() => es.emitRaw('{not_json'))
      // State stays running (it never crashed)
      expect(result.current.state?.state).toBe('running')
      expect(consoleWarn).toHaveBeenCalled()
    } finally {
      consoleWarn.mockRestore()
    }
  })
})

// ---------------------------------------------------------------------------
// FP27 A4 — useCopySession.resolveConflict removed
//
// At HEAD the hook exports a `resolveConflict(req)` callback that logs a
// console.warn and locally clears the conflict state — there is no
// /api/copy/resolve-conflict endpoint, so the user's choice is dropped on
// the floor. The wired UI buttons (keep/replace/skip in LibraryPage) thus
// appear interactive but actually do nothing. A4 removes the callback;
// the conflict prompt becomes a read-only banner.
//
// Pre-fix: hook returns an object with `resolveConflict: Function`.
// Post-fix: hook's returned object has no `resolveConflict` key.
// ---------------------------------------------------------------------------

describe('FP27 A4 — useCopySession.resolveConflict removed', () => {
  // DS04 T1.3: the file-level `beforeEach` at line 57 already stubs
  // globalThis.EventSource via `vi.stubGlobal` (with matching
  // `vi.unstubAllGlobals` in afterEach), and RTL's auto-cleanup covers
  // teardown. The nested hooks that were here bypassed `vi.stubGlobal`
  // (direct globalThis mutation that the file-level
  // `vi.unstubAllGlobals` couldn't see) and added redundant cleanup.
  // Both removed; the file-level setup applies to nested describes too.

  it('hook return value has no resolveConflict key', () => {
    const { result } = renderHook(() => useCopySession(), {
      wrapper: renderWithClient(),
    })
    expect(result.current).not.toHaveProperty('resolveConflict')
  })
})
