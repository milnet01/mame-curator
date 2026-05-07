import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'

import { server, http, HttpResponse } from '@/test/handlers'
import { useCopySession } from '../useCopySession'

// ---------------------------------------------------------------------------
// MockEventSource — jsdom has no native EventSource
// ---------------------------------------------------------------------------

class MockEventSource {
  static instances: MockEventSource[] = []
  url: string
  onmessage: ((ev: MessageEvent) => void) | null = null
  onerror: ((ev: Event) => void) | null = null
  closed = false

  constructor(url: string) {
    this.url = url
    MockEventSource.instances.push(this)
  }

  emit(data: unknown) {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }))
  }

  close() {
    this.closed = true
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
  cleanup()
  vi.unstubAllGlobals()
})

function renderWithClient() {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
}

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
})
