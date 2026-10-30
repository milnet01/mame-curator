import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";

import { strings } from "@/strings";
import { CopyModal, type CopyModalState } from "../CopyModal";

const baseState: CopyModalState = {
  jobId: "job-1",
  state: "running",
  filesDone: 1,
  filesTotal: 3,
  bytesDone: 100,
  bytesTotal: 300,
  currentFile: "pacman.zip",
  warnings: [],
};

// Render the modal in its default running state and click Cancel to open
// the keep/recycle abort prompt; returns the onAbort spy so the caller can
// assert which path the user picks.
async function openAbortPrompt(user: ReturnType<typeof userEvent.setup>) {
  const onAbort = vi.fn();
  render(
    <CopyModal
      open
      onOpenChange={() => {}}
      state={baseState}
      onPause={() => {}}
      onResume={() => {}}
      onAbort={onAbort}
    />,
  );
  await user.click(screen.getByRole("button", { name: /cancel/i }));
  return onAbort;
}

describe("CopyModal", () => {
  it("renders the progress line and current file", () => {
    render(
      <CopyModal
        open
        onOpenChange={() => {}}
        state={baseState}
        onPause={() => {}}
        onResume={() => {}}
        onAbort={() => {}}
      />,
    );
    expect(screen.getByText(/1 \/ 3/)).toBeInTheDocument();
    expect(screen.getByText(/pacman\.zip/)).toBeInTheDocument();
  });

  // mame-curator-1103 F2: "0 / 0" reads as the job having zero files, not
  // as "no job_started yet". Investigation: "'0 / 0' ... is the modal's
  // initial state before job_started arrives." While running with
  // filesTotal still 0 (no job_started received), the "0 / 0" progress
  // line must not render.
  it('does not render "0 / 0" while running with no job_started yet (mame-curator-1103 F2)', () => {
    render(
      <CopyModal
        open
        onOpenChange={() => {}}
        state={{ ...baseState, filesDone: 0, filesTotal: 0, currentFile: "" }}
        onPause={() => {}}
        onResume={() => {}}
        onAbort={() => {}}
      />,
    );
    expect(
      screen.queryByText(/0 \/ 0/),
      '"0 / 0" progress line rendered before job_started populated filesTotal',
    ).not.toBeInTheDocument();
  });

  it("shows pause when running and resume when paused", async () => {
    const user = userEvent.setup();
    const onPause = vi.fn();
    const onResume = vi.fn();
    const { rerender } = render(
      <CopyModal
        open
        onOpenChange={() => {}}
        state={baseState}
        onPause={onPause}
        onResume={onResume}
        onAbort={() => {}}
      />,
    );
    await user.click(screen.getByRole("button", { name: /pause/i }));
    expect(onPause).toHaveBeenCalledOnce();

    rerender(
      <CopyModal
        open
        onOpenChange={() => {}}
        state={{ ...baseState, state: "paused" }}
        onPause={onPause}
        onResume={onResume}
        onAbort={() => {}}
      />,
    );
    await user.click(screen.getByRole("button", { name: /resume/i }));
    expect(onResume).toHaveBeenCalledOnce();
  });

  it("opens the abort prompt offering BOTH keep + recycle paths (FP11 § A3)", async () => {
    const user = userEvent.setup();
    await openAbortPrompt(user);
    // Spec / design §9: "Cancel asks whether to keep already-copied
    // files or remove them." Both paths must be reachable.
    expect(
      await screen.findByRole("button", { name: /keep files/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /move to recycle bin/i }),
    ).toBeInTheDocument();
  });

  it("aborts with recycle_partial=true when user picks recycle", async () => {
    const user = userEvent.setup();
    const onAbort = await openAbortPrompt(user);
    await user.click(
      await screen.findByRole("button", { name: /move to recycle bin/i }),
    );
    expect(onAbort).toHaveBeenCalledWith({ recycle_partial: true });
  });

  it("aborts with recycle_partial=false when user picks keep", async () => {
    const user = userEvent.setup();
    const onAbort = await openAbortPrompt(user);
    await user.click(
      await screen.findByRole("button", { name: /keep files/i }),
    );
    expect(onAbort).toHaveBeenCalledWith({ recycle_partial: false });
  });

  it("shows a Done button in terminal states (FP11 § D8)", async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    const { rerender } = render(
      <CopyModal
        open
        onOpenChange={onOpenChange}
        state={{ ...baseState, state: "finished", finishedStatus: "OK" }}
        onPause={() => {}}
        onResume={() => {}}
        onAbort={() => {}}
      />,
    );
    const done = screen.getByRole("button", { name: /^done$/i });
    expect(done).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /pause/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /^cancel$/i })).toBeNull();
    await user.click(done);
    expect(onOpenChange).toHaveBeenCalledWith(false);

    rerender(
      <CopyModal
        open
        onOpenChange={onOpenChange}
        state={{ ...baseState, state: "aborted", abortReason: "CANCELLED" }}
        onPause={() => {}}
        onResume={() => {}}
        onAbort={() => {}}
      />,
    );
    expect(screen.getByRole("button", { name: /^done$/i })).toBeInTheDocument();
  });
});

describe("CopyModal — mame-curator-1144 copy honesty", () => {
  function renderModal(
    state: Partial<CopyModalState>,
    onOpenChange: (open: boolean) => void = () => {},
  ) {
    const ui = (next: Partial<CopyModalState>) => (
      <MemoryRouter>
        <CopyModal
          open
          onOpenChange={onOpenChange}
          state={{ ...baseState, ...next }}
          onPause={() => {}}
          onResume={() => {}}
          onAbort={() => {}}
        />
      </MemoryRouter>
    );
    const view = render(ui(state));
    return {
      ...view,
      update: (next: Partial<CopyModalState>) => view.rerender(ui(next)),
    };
  }

  it.each(["running", "paused", "terminating"] as const)(
    "cannot be dismissed while %s: no close button, and Esc does nothing",
    async (jobState) => {
      const user = userEvent.setup();
      const onOpenChange = vi.fn();
      renderModal({ state: jobState }, onOpenChange);
      expect(screen.queryByRole("button", { name: /close/i })).toBeNull();
      await user.keyboard("{Escape}");
      expect(onOpenChange).not.toHaveBeenCalled();
    },
  );

  it("can be dismissed once the connection is lost, since no control is left", async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    renderModal({ connection: "lost" }, onOpenChange);
    await user.click(screen.getByRole("button", { name: /^done$/i }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
    onOpenChange.mockClear();
    await user.keyboard("{Escape}");
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("says a clean finish plainly", () => {
    renderModal({ state: "finished", finishedStatus: "OK" });
    expect(screen.getByRole("status")).toHaveTextContent(
      strings.guide.copying.finishedHeading,
    );
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("announces a partial failure and links to Activity", () => {
    renderModal({ state: "finished", finishedStatus: "PARTIAL_FAILURE" });
    expect(screen.getByRole("alert")).toHaveTextContent(
      strings.guide.copying.partial,
    );
    expect(
      screen.getByRole("link", { name: strings.guide.copying.seeWhich }),
    ).toHaveAttribute("href", "/activity");
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("announces a crash with its reason, and never as Cancelled", () => {
    renderModal({ state: "aborted", abortReason: "boom" });
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent(strings.copy.failed);
    expect(alert).toHaveTextContent(strings.copy.failedDetail("boom"));
    expect(
      screen.queryByText(new RegExp(strings.copy.sessionState.aborted)),
    ).toBeNull();
  });

  it("shows the user's own Cancel without an alert", () => {
    renderModal({ state: "aborted", abortReason: "CANCELLED" });
    expect(screen.queryByRole("alert")).toBeNull();
    expect(
      screen.getByText(new RegExp(strings.copy.sessionState.aborted)),
    ).toBeInTheDocument();
  });

  it("says when the connection is lost, with no controls and no claim to be copying", () => {
    renderModal({ connection: "lost" });
    expect(screen.getByRole("alert")).toHaveTextContent(strings.copy.lost);
    expect(screen.queryByTestId("progress-line")).toBeNull();
    expect(screen.queryByRole("progressbar")).toBeNull();
    expect(screen.queryByRole("button", { name: /pause/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /^cancel$/i })).toBeNull();
    expect(
      screen.queryByText(new RegExp(strings.copy.sessionState.running)),
    ).toBeNull();
  });

  it("says when the connection has dropped, and keeps the controls", () => {
    renderModal({ connection: "reconnecting" });
    expect(screen.getByRole("alert")).toHaveTextContent(
      strings.copy.reconnecting,
    );
    expect(screen.getByRole("button", { name: /pause/i })).toBeInTheDocument();
  });

  it("shows a failed control while the copy is live, but not after it ended", () => {
    const { update } = renderModal({ controlError: "Pause failed" });
    expect(screen.getByRole("alert")).toHaveTextContent("Pause failed");
    update({
      controlError: "Pause failed",
      state: "finished",
      finishedStatus: "OK",
    });
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("keeps focus on the button when Pause becomes Resume", async () => {
    const user = userEvent.setup();
    const { update } = renderModal({});
    await user.click(screen.getByRole("button", { name: /pause/i }));
    const pressed = document.activeElement;
    update({ state: "paused" });
    expect(screen.getByRole("button", { name: /resume/i })).toBe(pressed);
    expect(document.activeElement).toBe(pressed);
  });

  it("closes the abort prompt if the job ends behind it", async () => {
    const user = userEvent.setup();
    const { update } = renderModal({});
    await user.click(screen.getByRole("button", { name: /cancel/i }));
    expect(await screen.findByRole("alertdialog")).toBeInTheDocument();
    update({ state: "finished", finishedStatus: "OK" });
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
  });
});
