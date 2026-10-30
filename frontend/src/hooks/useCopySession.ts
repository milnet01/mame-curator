import { useCallback, useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/api/client";
import { apiErrorMessage } from "@/lib/apiErrorToast";
import { strings } from "@/strings";
import {
  JobAcceptedSchema,
  JobStatusSchema,
  type CopyJobRequest,
  type JobAccepted,
  type JobStatus,
  type JobEventName,
} from "@/api/types";
import type { CopyModalState } from "@/components/library/CopyModal";

interface JobEventMsg {
  event: JobEventName;
  payload: Record<string, unknown>;
  ts: string;
}

/**
 * P15 § 4.3.3 — drives CopyModal's state from /api/copy/start +
 * /api/copy/status SSE stream.
 *
 * Event shape mirrors src/mame_curator/api/schemas.py JobEvent:
 *   { event: <literal>, payload: dict, ts: ISO8601 }
 *
 * FP27 A4: there is no /api/copy/resolve-conflict endpoint, and a conflict
 * never becomes an SSE event: the start's 409 is the only signal.
 *
 * SSE source torn down on terminal state, reset(), or unmount.
 */
export function useCopySession() {
  const [state, setState] = useState<CopyModalState | null>(null);
  const esRef = useRef<EventSource | null>(null);
  // FP24-J: unmounted flag so onSuccess returning AFTER an unmount
  // doesn't open an orphan stream we can't close.
  const cancelledRef = useRef(false);

  const closeStream = useCallback(() => {
    esRef.current?.close();
    esRef.current = null;
  }, []);

  // Tear down SSE on unmount. StrictMode's rehearsal unmounts and remounts,
  // so the mount has to clear the flag again.
  useEffect(() => {
    cancelledRef.current = false;
    return () => {
      cancelledRef.current = true;
      closeStream();
    };
  }, [closeStream]);

  const controlFailed = (words: string, err: unknown) =>
    setState(
      (prev) =>
        prev && {
          ...prev,
          controlError: `${words} ${apiErrorMessage(err)}`,
        },
    );
  const clearControlError = () =>
    setState((prev) => prev && { ...prev, controlError: undefined });

  const startMutation = useMutation({
    mutationFn: (req: CopyJobRequest) =>
      apiRequest<JobAccepted>("/api/copy/start", JobAcceptedSchema, {
        method: "POST",
        body: req,
      }),
    onSuccess: (data) => {
      // FP24-J: bail if the consumer unmounted during the start mutation
      // in flight; opening a fresh EventSource would leak it past the
      // component lifecycle.
      if (cancelledRef.current) return;
      // FP24-H: a second start() before the first stream terminates
      // must close the orphan stream so it doesn't keep dispatching
      // events into a hook whose state has moved on.
      closeStream();
      setState({
        jobId: data.job_id,
        state: "running",
        filesDone: 0,
        filesTotal: 0,
        bytesDone: 0,
        bytesTotal: 0,
        currentFile: "",
        warnings: [],
      });
      const es = new EventSource("/api/copy/status");
      es.onmessage = (ev: MessageEvent) => {
        // FP24-K: malformed SSE data must not crash the hook (React
        // doesn't catch synchronous exceptions inside event-handler
        // listeners).
        let parsed: JobEventMsg | null;
        try {
          parsed = JSON.parse(ev.data as string) as JobEventMsg | null;
        } catch (err) {
          console.warn("useCopySession: discarded malformed SSE event", err);
          return;
        }
        if (!parsed?.payload) {
          console.warn("useCopySession: discarded malformed SSE event", parsed);
          return;
        }
        const msg = parsed;
        setState((current) => {
          if (!current) return current;
          const prev = current.connection
            ? { ...current, connection: undefined }
            : current;
          switch (msg.event) {
            case "job_started":
              // A reconnect replays history from here, so this is no state
              // change, and the warnings are about to be sent again.
              return {
                ...prev,
                warnings: [],
                filesTotal:
                  (msg.payload.files_total as number | undefined) ??
                  prev.filesTotal,
                bytesTotal:
                  (msg.payload.bytes_total as number | undefined) ??
                  prev.bytesTotal,
              };
            case "file_started":
              return {
                ...prev,
                currentFile:
                  (msg.payload.short_name as string | undefined) ??
                  (msg.payload.name as string | undefined) ??
                  prev.currentFile,
              };
            case "file_progress":
              return {
                ...prev,
                filesDone:
                  (msg.payload.files_done as number | undefined) ??
                  prev.filesDone,
                bytesDone:
                  (msg.payload.bytes_done as number | undefined) ??
                  prev.bytesDone,
              };
            // A replay's paused or resumed cannot undo an accepted abort.
            case "paused":
              return prev.state === "terminating"
                ? prev
                : { ...prev, state: "paused" };
            case "resumed":
              return prev.state === "terminating"
                ? prev
                : { ...prev, state: "running" };
            case "bios_warning":
              return {
                ...prev,
                // mame-curator-1110: the server sends {name, kind}
                // (api/jobs.py JobManager.start), never a message.
                warnings: [
                  ...prev.warnings,
                  strings.copy.biosWarning(
                    String(msg.payload.name ?? "?"),
                    String(msg.payload.kind ?? "unknown"),
                  ),
                ],
              };
            case "job_finished":
              closeStream();
              return {
                ...prev,
                state: "finished",
                finishedStatus: msg.payload.status as string | undefined,
                biosMissing: msg.payload.bios_missing as number | undefined,
              };
            case "job_aborted":
              closeStream();
              return {
                ...prev,
                state: "aborted",
                abortReason: msg.payload.reason as string | undefined,
              };
            case "file_finished":
              // mame-curator-1103: the server's job-wide count, not a local
              // tally, so a reconnect replay cannot double-count.
              return {
                ...prev,
                filesDone:
                  (msg.payload.files_done as number | undefined) ??
                  prev.filesDone,
              };
            default:
              return prev;
          }
        });
      };
      // FP24-I: only close on a terminal failure (readyState===CLOSED).
      // Browsers auto-reconnect on transient drops with readyState
      // back at CONNECTING; closing in that state defeats reconnect.
      es.onerror = () => {
        const closed = es.readyState === EventSource.CLOSED;
        if (closed) closeStream();
        setState(
          (prev) =>
            prev && { ...prev, connection: closed ? "lost" : "reconnecting" },
        );
      };
      es.onopen = () => {
        setState((prev) => prev && { ...prev, connection: undefined });
      };
      esRef.current = es;
    },
  });

  const pauseMutation = useMutation({
    mutationFn: () =>
      apiRequest<JobStatus>("/api/copy/pause", JobStatusSchema, {
        method: "POST",
      }),
    onMutate: clearControlError,
    onError: (err) => controlFailed(strings.copy.pauseFailed, err),
  });

  const resumeMutation = useMutation({
    mutationFn: () =>
      apiRequest<JobStatus>("/api/copy/resume", JobStatusSchema, {
        method: "POST",
      }),
    onMutate: clearControlError,
    onError: (err) => controlFailed(strings.copy.resumeFailed, err),
  });

  const abortMutation = useMutation({
    mutationFn: (req: { recycle_partial: boolean }) =>
      apiRequest<JobStatus>("/api/copy/abort", JobStatusSchema, {
        method: "POST",
        body: req,
      }),
    onMutate: clearControlError,
    onError: (err) => controlFailed(strings.copy.abortFailed, err),
    // No event says this, and the job may have ended before the reply came.
    onSuccess: () =>
      setState((prev) =>
        prev?.state === "running" || prev?.state === "paused"
          ? { ...prev, state: "terminating" }
          : prev,
      ),
  });

  const reset = useCallback(() => {
    closeStream();
    setState(null);
  }, [closeStream]);

  return {
    state,
    start: startMutation.mutate,
    isStarting: startMutation.isPending,
    pause: pauseMutation.mutate,
    resume: resumeMutation.mutate,
    abort: abortMutation.mutate,
    reset,
  };
}
