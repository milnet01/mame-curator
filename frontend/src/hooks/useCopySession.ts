import { useCallback, useEffect, useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { apiRequest } from '@/api/client'
import {
  JobAcceptedSchema,
  JobStatusSchema,
  type CopyJobRequest,
  type JobAccepted,
  type JobStatus,
  type JobEventName,
} from '@/api/types'
import type { CopyModalState } from '@/components/library/CopyModal'

interface JobEventMsg {
  event: JobEventName
  payload: Record<string, unknown>
  ts: string
}

/**
 * P15 § 4.3.3 — drives CopyModal's state from /api/copy/start +
 * /api/copy/status SSE stream.
 *
 * Event shape mirrors src/mame_curator/api/schemas.py JobEvent:
 *   { event: <literal>, payload: dict, ts: ISO8601 }
 *
 * FP27 A4: there is no /api/copy/resolve-conflict endpoint. Mid-flight
 * conflicts surface via the modal's `state.conflict` field as a read-
 * only banner; the only resolution path is abort + restart with an
 * updated CopyJobRequest.append_decisions. The prior `resolveConflict`
 * callback (silently dropped the user's choice) was removed.
 *
 * SSE source torn down on terminal state, reset(), or unmount.
 */
export function useCopySession() {
  const [state, setState] = useState<CopyModalState | null>(null)
  const esRef = useRef<EventSource | null>(null)
  // FP24-J: unmounted/cancelled flag so onSuccess returning AFTER an
  // unmount or reset() doesn't open an orphan stream we can't close.
  const cancelledRef = useRef(false)

  const closeStream = useCallback(() => {
    esRef.current?.close()
    esRef.current = null
  }, [])

  // Tear down SSE on unmount
  useEffect(
    () => () => {
      cancelledRef.current = true
      closeStream()
    },
    [closeStream],
  )

  const startMutation = useMutation({
    mutationFn: (req: CopyJobRequest) =>
      apiRequest<JobAccepted>('/api/copy/start', JobAcceptedSchema, {
        method: 'POST',
        body: req,
      }),
    onSuccess: (data) => {
      // FP24-J: bail if the consumer unmounted or reset() during the
      // start mutation in flight; opening a fresh EventSource would
      // leak it past the component lifecycle.
      if (cancelledRef.current) return
      // FP24-H: a second start() before the first stream terminates
      // must close the orphan stream so it doesn't keep dispatching
      // events into a hook whose state has moved on.
      closeStream()
      setState({
        jobId: data.job_id,
        state: 'running',
        filesDone: 0,
        filesTotal: 0,
        bytesDone: 0,
        bytesTotal: 0,
        currentFile: '',
        warnings: [],
        conflict: null,
      })
      const es = new EventSource('/api/copy/status')
      es.onmessage = (ev: MessageEvent) => {
        // FP24-K: malformed SSE data must not crash the hook (React
        // doesn't catch synchronous exceptions inside event-handler
        // listeners).
        let msg: JobEventMsg
        try {
          msg = JSON.parse(ev.data as string) as JobEventMsg
        } catch (err) {
          console.warn('useCopySession: discarded malformed SSE event', err)
          return
        }
        setState((prev) => {
          if (!prev) return prev
          switch (msg.event) {
            case 'job_started':
              return {
                ...prev,
                state: 'running',
                filesTotal: (msg.payload.files_total as number | undefined) ?? prev.filesTotal,
                bytesTotal: (msg.payload.bytes_total as number | undefined) ?? prev.bytesTotal,
              }
            case 'file_started':
              return {
                ...prev,
                currentFile:
                  (msg.payload.short_name as string | undefined) ??
                  (msg.payload.name as string | undefined) ??
                  prev.currentFile,
              }
            case 'file_progress':
              return {
                ...prev,
                filesDone: (msg.payload.files_done as number | undefined) ?? prev.filesDone,
                bytesDone: (msg.payload.bytes_done as number | undefined) ?? prev.bytesDone,
              }
            case 'paused':
              return { ...prev, state: 'paused' }
            case 'resumed':
              return { ...prev, state: 'running' }
            case 'bios_warning':
              return {
                ...prev,
                warnings: [
                  ...prev.warnings,
                  (msg.payload.message as string | undefined) ?? 'BIOS warning',
                ],
              }
            case 'job_finished':
              closeStream()
              return { ...prev, state: 'finished' }
            case 'job_aborted':
              closeStream()
              return { ...prev, state: 'aborted' }
            case 'file_finished':
            default:
              return prev
          }
        })
      }
      // FP24-I: only close on a terminal failure (readyState===CLOSED).
      // Browsers auto-reconnect on transient drops with readyState
      // back at CONNECTING; closing in that state defeats reconnect.
      es.onerror = () => {
        if (es.readyState === EventSource.CLOSED) closeStream()
      }
      esRef.current = es
    },
  })

  const pauseMutation = useMutation({
    mutationFn: () =>
      apiRequest<JobStatus>('/api/copy/pause', JobStatusSchema, { method: 'POST' }),
  })

  const resumeMutation = useMutation({
    mutationFn: () =>
      apiRequest<JobStatus>('/api/copy/resume', JobStatusSchema, { method: 'POST' }),
  })

  const abortMutation = useMutation({
    mutationFn: (req: { recycle_partial: boolean }) =>
      apiRequest<JobStatus>('/api/copy/abort', JobStatusSchema, {
        method: 'POST',
        body: req,
      }),
  })

  const reset = useCallback(() => {
    closeStream()
    setState(null)
  }, [closeStream])

  return {
    state,
    start: startMutation.mutate,
    pause: pauseMutation.mutate,
    resume: resumeMutation.mutate,
    abort: abortMutation.mutate,
    reset,
  }
}
