import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, configure, renderHook, waitFor } from "@testing-library/react";

import { server, http, HttpResponse } from "@/test/handlers";
import { makeClientWrapper } from "@/test/renderWithClient";
import { useCopySession } from "../useCopySession";
import { strings } from "@/strings";

// ---------------------------------------------------------------------------
// MockEventSource — jsdom has no native EventSource
// ---------------------------------------------------------------------------

class MockEventSource {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSED = 2;
  static instances: MockEventSource[] = [];
  url: string;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  onopen: ((ev: Event) => void) | null = null;
  closed = false;
  readyState = MockEventSource.OPEN;

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  emit(data: unknown) {
    this.onmessage?.(
      new MessageEvent("message", { data: JSON.stringify(data) }),
    );
  }

  // Helpers for FP24-I (transient drop) and FP24-K (parse error).
  emitRaw(raw: string) {
    this.onmessage?.(new MessageEvent("message", { data: raw }));
  }
  emitTransientError() {
    // Browser EventSource keeps readyState at CONNECTING during retry.
    this.readyState = MockEventSource.CONNECTING;
    this.onerror?.(new Event("error"));
  }
  emitTerminalError() {
    this.readyState = MockEventSource.CLOSED;
    this.onerror?.(new Event("error"));
  }
  emitOpen() {
    this.readyState = MockEventSource.OPEN;
    this.onopen?.(new Event("open"));
  }

  close() {
    this.closed = true;
    this.readyState = MockEventSource.CLOSED;
  }
}

// ---------------------------------------------------------------------------
// Test setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.stubGlobal("EventSource", MockEventSource);
  MockEventSource.instances = [];

  server.use(
    http.post("/api/copy/start", () =>
      HttpResponse.json({ job_id: "job-123" }),
    ),
    http.post("/api/copy/pause", () =>
      HttpResponse.json({
        job_id: "job-123",
        state: "paused",
        started_at: "2026-05-07T20:00:00Z",
        files_done: 0,
        files_total: 1,
        bytes_done: 0,
        bytes_total: 1024,
      }),
    ),
    http.post("/api/copy/resume", () =>
      HttpResponse.json({
        job_id: "job-123",
        state: "running",
        started_at: "2026-05-07T20:00:00Z",
        files_done: 0,
        files_total: 1,
        bytes_done: 0,
        bytes_total: 1024,
      }),
    ),
    http.post("/api/copy/abort", () =>
      HttpResponse.json({
        job_id: "job-123",
        state: "terminating",
        started_at: "2026-05-07T20:00:00Z",
        files_done: 0,
        files_total: 1,
        bytes_done: 0,
        bytes_total: 1024,
      }),
    ),
  );
});

afterEach(() => {
  // FP31: removed redundant explicit `cleanup()` — vitest `globals: true`
  // enables RTL's auto-cleanup. The sibling hook-test files dropped this
  // during DS04 T3.1; useCopySession.test.tsx was missed in that pass.
  vi.unstubAllGlobals();
});

const renderWithClient = makeClientWrapper;

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("useCopySession", () => {
  it("starts in null state", () => {
    const { result } = renderHook(() => useCopySession(), {
      wrapper: renderWithClient(),
    });
    expect(result.current.state).toBeNull();
  });

  it("after start() + job_started SSE event, state.jobId and state.state populate", async () => {
    const { result } = renderHook(() => useCopySession(), {
      wrapper: renderWithClient(),
    });
    act(() => {
      result.current.start({
        selected_names: ["pacman"],
        conflict_strategy: "CANCEL",
        append_decisions: {},
      });
    });
    await waitFor(() => expect(MockEventSource.instances).toHaveLength(1));
    act(() => {
      MockEventSource.instances[0].emit({
        event: "job_started",
        payload: { files_total: 1, bytes_total: 1024 },
        ts: new Date().toISOString(),
      });
    });
    await waitFor(() => {
      expect(result.current.state?.jobId).toBe("job-123");
      expect(result.current.state?.state).toBe("running");
      expect(result.current.state?.filesTotal).toBe(1);
    });
  });

  it("file_started + file_progress events update currentFile and filesDone", async () => {
    const { result } = renderHook(() => useCopySession(), {
      wrapper: renderWithClient(),
    });
    act(() => {
      result.current.start({
        selected_names: ["pacman"],
        conflict_strategy: "CANCEL",
        append_decisions: {},
      });
    });
    await waitFor(() => expect(MockEventSource.instances).toHaveLength(1));
    act(() => {
      const es = MockEventSource.instances[0];
      es.emit({
        event: "job_started",
        payload: { files_total: 1, bytes_total: 1024 },
        ts: new Date().toISOString(),
      });
      es.emit({
        event: "file_started",
        payload: { short_name: "pacman" },
        ts: new Date().toISOString(),
      });
      es.emit({
        event: "file_progress",
        payload: { files_done: 1, bytes_done: 1024 },
        ts: new Date().toISOString(),
      });
    });
    await waitFor(() => {
      expect(result.current.state?.filesDone).toBe(1);
      expect(result.current.state?.currentFile).toBe("pacman");
    });
  });

  // mame-curator-1103 F1: file_finished must count toward filesDone by
  // READING payload.files_done, not by incrementing a local per-event
  // counter. Investigation: "useCopySession never counts done files.
  // file_progress carries no files_done, and the hook ignores
  // file_finished." Pre-fix, `case 'file_finished':` falls through to
  // `default: return prev` — the event is silently dropped and filesDone
  // never advances on it.
  //
  // The second file_finished jumps files_done straight from 1 to 3 (not
  // to 2) on purpose: an SSE reconnect replays history, and a fix that
  // increments a local counter once per received file_finished event
  // (instead of adopting the payload's own running count) would
  // double-count on replay and diverge from the server's true total.
  // Asserting filesDone === 3 after a payload of files_done: 3 catches
  // that route; asserting === 2 after two events would not.
  it("file_finished event with files_done sets state.filesDone (mame-curator-1103 F1)", async () => {
    const { result } = renderHook(() => useCopySession(), {
      wrapper: renderWithClient(),
    });
    act(() => {
      result.current.start({
        selected_names: ["pacman"],
        conflict_strategy: "CANCEL",
        append_decisions: {},
      });
    });
    await waitFor(() => expect(MockEventSource.instances).toHaveLength(1));
    const es = MockEventSource.instances[0];
    act(() => {
      es.emit({
        event: "job_started",
        payload: { files_total: 3, bytes_total: 1024 },
        ts: new Date().toISOString(),
      });
      es.emit({
        event: "file_finished",
        payload: { short_name: "pacman", files_done: 1, bytes: 1024 },
        ts: new Date().toISOString(),
      });
    });
    await waitFor(() => {
      expect(result.current.state?.filesDone).toBe(1);
    });
    act(() => {
      es.emit({
        event: "file_finished",
        payload: { short_name: "galaga", files_done: 3, bytes: 1024 },
        ts: new Date().toISOString(),
      });
    });
    await waitFor(() => {
      expect(result.current.state?.filesDone).toBe(3);
    });
  });

  // mame-curator-1110: the server sends bios_warning as {name, kind}
  // (api/jobs.py JobManager.start). Pre-fix the hook read payload.message,
  // which never exists, so every warning rendered as a bare "BIOS warning".
  it("bios_warning names the machine and the reason (mame-curator-1110)", async () => {
    const { result } = renderHook(() => useCopySession(), {
      wrapper: renderWithClient(),
    });
    act(() => {
      result.current.start({
        selected_names: ["sf2"],
        conflict_strategy: "CANCEL",
        append_decisions: {},
      });
    });
    await waitFor(() => expect(MockEventSource.instances).toHaveLength(1));
    const es = MockEventSource.instances[0];
    act(() => {
      es.emit({
        event: "bios_warning",
        payload: { name: "sf2", kind: "missing_from_listxml" },
        ts: new Date().toISOString(),
      });
    });
    await waitFor(() => {
      expect(result.current.state?.warnings).toEqual([
        strings.copy.biosWarning("sf2", "missing_from_listxml"),
      ]);
    });
    expect(result.current.state?.warnings[0]).toContain("sf2");
  });

  it("keeps the count of BIOS files job_finished says were missing", async () => {
    const { result } = renderHook(() => useCopySession(), {
      wrapper: renderWithClient(),
    });
    act(() => {
      result.current.start({
        selected_names: ["sf2"],
        conflict_strategy: "CANCEL",
        append_decisions: {},
      });
    });
    await waitFor(() => expect(MockEventSource.instances).toHaveLength(1));
    act(() => {
      MockEventSource.instances[0].emit({
        event: "job_finished",
        payload: { status: "OK", bios_missing: 2 },
        ts: new Date().toISOString(),
      });
    });
    await waitFor(() => expect(result.current.state?.biosMissing).toBe(2));
  });

  it("job_finished closes the SSE source and flips state to finished", async () => {
    const { result } = renderHook(() => useCopySession(), {
      wrapper: renderWithClient(),
    });
    act(() => {
      result.current.start({
        selected_names: ["pacman"],
        conflict_strategy: "CANCEL",
        append_decisions: {},
      });
    });
    await waitFor(() => expect(MockEventSource.instances).toHaveLength(1));
    const es = MockEventSource.instances[0];
    act(() => {
      es.emit({
        event: "job_finished",
        payload: {},
        ts: new Date().toISOString(),
      });
    });
    await waitFor(() => {
      expect(result.current.state?.state).toBe("finished");
      expect(es.closed).toBe(true);
    });
  });

  it("reset() clears state and closes any open SSE", async () => {
    const { result } = renderHook(() => useCopySession(), {
      wrapper: renderWithClient(),
    });
    act(() => {
      result.current.start({
        selected_names: ["pacman"],
        conflict_strategy: "CANCEL",
        append_decisions: {},
      });
    });
    await waitFor(() => expect(MockEventSource.instances).toHaveLength(1));
    act(() => result.current.reset());
    expect(result.current.state).toBeNull();
    expect(MockEventSource.instances[0].closed).toBe(true);
  });

  // FP24-H: a second start() call before the first stream terminates
  // must close the orphan stream so it doesn't keep dispatching events
  // into a hook whose state has moved on.
  it("a second start() closes the previous stream", async () => {
    const { result } = renderHook(() => useCopySession(), {
      wrapper: renderWithClient(),
    });
    act(() => {
      result.current.start({
        selected_names: ["a"],
        conflict_strategy: "CANCEL",
        append_decisions: {},
      });
    });
    await waitFor(() => expect(MockEventSource.instances).toHaveLength(1));
    act(() => {
      result.current.start({
        selected_names: ["b"],
        conflict_strategy: "CANCEL",
        append_decisions: {},
      });
    });
    await waitFor(() => expect(MockEventSource.instances).toHaveLength(2));
    expect(MockEventSource.instances[0].closed).toBe(true);
  });

  // FP24-I: onerror with a transient (CONNECTING) readyState means the
  // browser is auto-reconnecting; we must not unconditionally close.
  it("transient SSE error does NOT close the stream", async () => {
    const { result } = renderHook(() => useCopySession(), {
      wrapper: renderWithClient(),
    });
    act(() => {
      result.current.start({
        selected_names: ["pacman"],
        conflict_strategy: "CANCEL",
        append_decisions: {},
      });
    });
    await waitFor(() => expect(MockEventSource.instances).toHaveLength(1));
    const es = MockEventSource.instances[0];
    act(() => es.emitTransientError());
    expect(es.closed).toBe(false);
  });

  it("terminal SSE error (readyState=CLOSED) closes the stream", async () => {
    const { result } = renderHook(() => useCopySession(), {
      wrapper: renderWithClient(),
    });
    act(() => {
      result.current.start({
        selected_names: ["pacman"],
        conflict_strategy: "CANCEL",
        append_decisions: {},
      });
    });
    await waitFor(() => expect(MockEventSource.instances).toHaveLength(1));
    const es = MockEventSource.instances[0];
    act(() => es.emitTerminalError());
    expect(es.closed).toBe(true);
  });

  // FP24-K: malformed SSE data must not crash the hook.
  it("malformed SSE payload is logged and discarded, hook state intact", async () => {
    const consoleWarn = vi.spyOn(console, "warn").mockImplementation(() => {});
    try {
      const { result } = renderHook(() => useCopySession(), {
        wrapper: renderWithClient(),
      });
      act(() => {
        result.current.start({
          selected_names: ["pacman"],
          conflict_strategy: "CANCEL",
          append_decisions: {},
        });
      });
      await waitFor(() => expect(MockEventSource.instances).toHaveLength(1));
      const es = MockEventSource.instances[0];
      // FP31: emit job_started first so `state.state === 'running'` is
      // the established precondition, not an implicit side effect of
      // `start()`. The malformed-payload contract is then unambiguous:
      // a bad message after a real running state must not flip state to
      // null / 'idle' / 'errored'.
      act(() =>
        es.emit({
          event: "job_started",
          payload: {
            job_id: "j1",
            files_total: 1,
            bytes_total: 1024,
            started_at: new Date().toISOString(),
          },
          ts: new Date().toISOString(),
        }),
      );
      await waitFor(() => expect(result.current.state?.state).toBe("running"));
      // Send raw garbage that JSON.parse throws on
      act(() => es.emitRaw("{not_json"));
      // State stays running (it never crashed)
      expect(result.current.state?.state).toBe("running");
      expect(consoleWarn).toHaveBeenCalled();
    } finally {
      consoleWarn.mockRestore();
    }
  });
});

// ---------------------------------------------------------------------------
// mame-curator-1144 — the hook never misreports a copy
// ---------------------------------------------------------------------------

async function startedSession(wrapper = renderWithClient()) {
  const hook = renderHook(() => useCopySession(), { wrapper });
  act(() => {
    hook.result.current.start({
      selected_names: ["pacman"],
      conflict_strategy: "CANCEL",
      append_decisions: {},
    });
  });
  await waitFor(() => expect(MockEventSource.instances).toHaveLength(1));
  const es = MockEventSource.instances[0];
  const send = (event: string, payload: Record<string, unknown> = {}) =>
    act(() => es.emit({ event, payload, ts: new Date().toISOString() }));
  send("job_started", { files_total: 2, bytes_total: 2048 });
  return { ...hook, es, send };
}

const failingControl = (path: string) =>
  server.use(
    http.post(path, () =>
      HttpResponse.json(
        { code: "job_not_found", detail: "no active copy job" },
        { status: 404 },
      ),
    ),
  );

describe("mame-curator-1144 — copy honesty", () => {
  it("keeps job_aborted's reason, so a crash can read differently from Stop", async () => {
    const { result, send } = await startedSession();
    send("job_aborted", { reason: "PlaylistError('disk full')" });
    expect(result.current.state?.state).toBe("aborted");
    expect(result.current.state?.abortReason).toBe(
      "PlaylistError('disk full')",
    );
  });

  it("a stream closed for good says the connection is lost", async () => {
    const { result, es } = await startedSession();
    act(() => es.emitTerminalError());
    expect(result.current.state?.connection).toBe("lost");
  });

  it("a dropped stream says so until it reconnects", async () => {
    const { result, es } = await startedSession();
    act(() => es.emitTransientError());
    expect(result.current.state?.connection).toBe("reconnecting");
    act(() => es.emitOpen());
    expect(result.current.state?.connection).toBeUndefined();
  });

  it("an event also clears the dropped-stream notice", async () => {
    const { result, es, send } = await startedSession();
    act(() => es.emitTransientError());
    send("file_finished", { files_done: 1 });
    expect(result.current.state?.connection).toBeUndefined();
  });

  it("a failed pause, resume or abort says so, and the next success clears it", async () => {
    const { result } = await startedSession();
    const cases: [string, () => void, string][] = [
      [
        "/api/copy/pause",
        () => result.current.pause(),
        strings.copy.pauseFailed,
      ],
      [
        "/api/copy/resume",
        () => result.current.resume(),
        strings.copy.resumeFailed,
      ],
      [
        "/api/copy/abort",
        () => result.current.abort({ recycle_partial: false }),
        strings.copy.abortFailed,
      ],
    ];
    for (const [path, act_, words] of cases) {
      failingControl(path);
      act(act_);
      await waitFor(() =>
        expect(result.current.state?.controlError).toContain(words),
      );
      expect(result.current.state?.state).toBe("running");
      server.resetHandlers();
      server.use(
        http.post(path, () =>
          HttpResponse.json({
            job_id: "job-123",
            state: "running",
            started_at: "2026-05-07T20:00:00Z",
            files_done: 0,
            files_total: 1,
            bytes_done: 0,
            bytes_total: 1024,
          }),
        ),
      );
      if (path !== "/api/copy/abort") {
        act(act_);
        await waitFor(() =>
          expect(result.current.state?.controlError).toBeUndefined(),
        );
      }
    }
  });

  it("an accepted abort shows as stopping, not as still running", async () => {
    const { result, send } = await startedSession();
    act(() => result.current.abort({ recycle_partial: false }));
    await waitFor(() =>
      expect(result.current.state?.state).toBe("terminating"),
    );
    send("job_aborted", { reason: "CANCELLED" });
    expect(result.current.state?.state).toBe("aborted");
  });

  it("an abort reply arriving after the job ended cannot revive it", async () => {
    const { result, send } = await startedSession();
    send("job_finished", { status: "OK" });
    act(() => result.current.abort({ recycle_partial: false }));
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(result.current.state?.state).toBe("finished");
  });

  it("a replay after a reconnect leaves a stopping copy stopping", async () => {
    const { result, send } = await startedSession();
    send("paused");
    act(() => result.current.abort({ recycle_partial: false }));
    await waitFor(() =>
      expect(result.current.state?.state).toBe("terminating"),
    );
    send("job_started", { files_total: 2, bytes_total: 2048 });
    expect(result.current.state?.state).toBe("terminating");
    send("paused");
    expect(result.current.state?.state).toBe("terminating");
    send("resumed");
    expect(result.current.state?.state).toBe("terminating");
  });

  it("a replay after a reconnect leaves a paused copy paused", async () => {
    const { result, send } = await startedSession();
    send("paused");
    send("job_started", { files_total: 2, bytes_total: 2048 });
    expect(result.current.state?.state).toBe("paused");
  });

  it("a replay does not repeat the warnings", async () => {
    const { result, send } = await startedSession();
    const warning = { name: "pacman", kind: "missing_from_listxml" };
    send("bios_warning", warning);
    send("job_started", { files_total: 2, bytes_total: 2048 });
    send("bios_warning", warning);
    expect(result.current.state?.warnings).toHaveLength(1);
  });

  it("valid JSON that is not an event is discarded", async () => {
    const consoleWarn = vi.spyOn(console, "warn").mockImplementation(() => {});
    try {
      const { result, es } = await startedSession();
      act(() => es.emitRaw("null"));
      act(() => es.emitRaw('{"event":"job_started"}'));
      expect(result.current.state?.state).toBe("running");
      expect(consoleWarn).toHaveBeenCalledTimes(2);
    } finally {
      consoleWarn.mockRestore();
    }
  });

  it("StrictMode's rehearsal unmount does not hide the copy", async () => {
    // React rehearses effects only when StrictMode is the outermost node, as
    // it is in main.tsx, so a StrictMode wrapper here would rehearse nothing.
    configure({ reactStrictMode: true });
    try {
      const { result } = renderHook(() => useCopySession(), {
        wrapper: renderWithClient(),
      });
      act(() => {
        result.current.start({
          selected_names: ["pacman"],
          conflict_strategy: "CANCEL",
          append_decisions: {},
        });
      });
      await waitFor(() => expect(result.current.state?.state).toBe("running"));
    } finally {
      configure({ reactStrictMode: false });
    }
  });

  it("isStarting is true until the start has answered", async () => {
    let answer = () => {};
    server.use(
      http.post(
        "/api/copy/start",
        () =>
          new Promise((resolve) => {
            answer = () => resolve(HttpResponse.json({ job_id: "job-123" }));
          }),
      ),
    );
    const { result } = renderHook(() => useCopySession(), {
      wrapper: renderWithClient(),
    });
    expect(result.current.isStarting).toBe(false);
    act(() => {
      result.current.start({
        selected_names: ["pacman"],
        conflict_strategy: "CANCEL",
        append_decisions: {},
      });
    });
    await waitFor(() => expect(result.current.isStarting).toBe(true));
    answer();
    await waitFor(() => expect(result.current.isStarting).toBe(false));
  });
});

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

describe("FP27 A4 — useCopySession.resolveConflict removed", () => {
  // DS04 T1.3: the file-level `beforeEach` at line 57 already stubs
  // globalThis.EventSource via `vi.stubGlobal` (with matching
  // `vi.unstubAllGlobals` in afterEach), and RTL's auto-cleanup covers
  // teardown. The nested hooks that were here bypassed `vi.stubGlobal`
  // (direct globalThis mutation that the file-level
  // `vi.unstubAllGlobals` couldn't see) and added redundant cleanup.
  // Both removed; the file-level setup applies to nested describes too.

  it("hook return value has no resolveConflict key", () => {
    const { result } = renderHook(() => useCopySession(), {
      wrapper: renderWithClient(),
    });
    expect(result.current).not.toHaveProperty("resolveConflict");
  });
});
