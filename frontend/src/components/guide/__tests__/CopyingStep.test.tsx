/**
 * mame-curator-1144 — the Copying step never misreports a copy, and a keyboard
 * or magnifier user keeps their place and a way to Resume.
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";

import type { CopyModalState } from "@/components/library/CopyModal";
import { strings } from "@/strings";
import { CopyingStep } from "../steps/CopyingStep";

const g = strings.guide;
const base: CopyModalState = {
  jobId: "job-1",
  state: "running",
  filesDone: 1,
  filesTotal: 3,
  bytesDone: 100,
  bytesTotal: 300,
  currentFile: "pacman",
  warnings: [],
};

function renderStep(state: Partial<CopyModalState> = {}) {
  const onAbort = vi.fn();
  const ui = (next: Partial<CopyModalState>) => (
    <MemoryRouter>
      <CopyingStep
        state={{ ...base, ...next }}
        stepNumber={5}
        stepCount={5}
        onPause={() => {}}
        onResume={() => {}}
        onAbort={onAbort}
        onCopyMore={() => {}}
      />
    </MemoryRouter>
  );
  const view = render(ui(state));
  return {
    onAbort,
    update: (next: Partial<CopyModalState>) => view.rerender(ui(next)),
  };
}

const heading = (name: string) =>
  expect(screen.getByRole("heading", { name })).toBeVisible();
const button = (name: string) => screen.queryByRole("button", { name });
const link = (name: string) => screen.queryByRole("link", { name });

describe("CopyingStep outcome", () => {
  it("says so when a BIOS file was missing, though the copy finished", () => {
    renderStep({ state: "finished", finishedStatus: "OK", biosMissing: 2 });
    heading(g.copying.finishedHeading);
    expect(screen.getByRole("alert")).toHaveTextContent(
      strings.copy.biosMissing(2),
    );
    expect(link(g.copying.seeWhich)).toBeNull();
  });

  it("says so on a partial finish too", () => {
    renderStep({
      state: "finished",
      finishedStatus: "PARTIAL_FAILURE",
      biosMissing: 1,
    });
    expect(screen.getByRole("alert")).toHaveTextContent(
      strings.copy.biosMissing(1),
    );
    expect(screen.getByRole("alert")).toHaveTextContent(g.copying.partial);
  });

  it("adds no alert to a clean finish", () => {
    renderStep({ state: "finished", finishedStatus: "OK", biosMissing: 0 });
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("the user's own Stop reads as stopped, with no alert", () => {
    renderStep({ state: "aborted", abortReason: "CANCELLED" });
    heading(g.copying.stoppedHeading);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("a crash reads as a failure: alert, reason and Activity", () => {
    renderStep({ state: "aborted", abortReason: "PlaylistError('full')" });
    heading(g.copying.failedHeading);
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent(strings.copy.failed);
    expect(alert).toHaveTextContent(
      strings.copy.failedDetail("PlaylistError('full')"),
    );
    expect(link(g.copying.seeWhich)).toHaveAttribute("href", "/activity");
    expect(button(g.copying.copyMore)).toBeVisible();
  });

  it("an aborted job with no reason is not taken for the user's Stop", () => {
    renderStep({ state: "aborted" });
    heading(g.copying.failedHeading);
    expect(screen.getByRole("alert")).toBeVisible();
  });

  it("a lost stream says so, and stops claiming to copy", () => {
    renderStep({ connection: "lost" });
    heading(g.copying.lostHeading);
    expect(screen.getByRole("alert")).toHaveTextContent(strings.copy.lost);
    expect(link(g.copying.seeWhich)).toHaveAttribute("href", "/activity");
    expect(button(strings.copy.pause)).toBeNull();
    expect(button(g.copying.stop)).toBeNull();
    expect(screen.queryByText(g.copying.closeHint)).toBeNull();
    expect(screen.queryByRole("progressbar")).toBeNull();
    expect(screen.queryByTestId("progress-line")).toBeNull();
    expect(button(g.copying.copyMore)).toBeVisible();
  });

  it("a lost stream while paused still has a way out", () => {
    renderStep({ state: "paused", connection: "lost" });
    expect(link(g.exit)).toBeVisible();
    expect(button(strings.copy.resume)).toBeNull();
  });

  it("a dropped stream says so and keeps the controls", () => {
    renderStep({ connection: "reconnecting" });
    expect(screen.getByRole("alert")).toHaveTextContent(
      strings.copy.reconnecting,
    );
    expect(button(strings.copy.pause)).toBeVisible();
  });

  it("the Activity link is a full-size guide action", () => {
    renderStep({ state: "finished", finishedStatus: "PARTIAL_FAILURE" });
    expect(link(g.copying.seeWhich)).toHaveClass("min-h-12");
  });

  it("a failed control is announced while the copy is live, not after", () => {
    const { update } = renderStep({ controlError: "Pause failed" });
    expect(screen.getByRole("alert")).toHaveTextContent("Pause failed");
    update({
      controlError: "Pause failed",
      state: "finished",
      finishedStatus: "OK",
    });
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("shows BIOS warnings while copying and beside a clean finish", () => {
    const warnings = ["pacman: its BIOS can't be worked out"];
    const { update } = renderStep({ warnings });
    expect(screen.getByText(g.copying.warningsLead)).toBeVisible();
    expect(screen.getByText(warnings[0])).toBeVisible();
    update({ warnings, state: "finished", finishedStatus: "OK" });
    expect(screen.getByText(warnings[0])).toBeVisible();
  });

  it("says nothing about warnings when there are none", () => {
    renderStep();
    expect(screen.queryByText(g.copying.warningsLead)).toBeNull();
  });

  it("a stopping copy says so in the heading, and offers no controls", () => {
    renderStep({ state: "terminating" });
    heading(g.copying.stoppingHeading);
    expect(button(strings.copy.pause)).toBeNull();
    expect(button(g.copying.stop)).toBeNull();
  });
});

describe("CopyingStep while paused", () => {
  it("offers only Resume and Stop: the exit is hidden", () => {
    renderStep({ state: "paused" });
    expect(link(g.exit)).toBeNull();
    expect(button(strings.copy.resume)).toBeVisible();
    expect(button(g.copying.stop)).toBeVisible();
  });

  it("gives the exit back when the copy runs again", () => {
    const { update } = renderStep({ state: "paused" });
    update({ state: "running" });
    expect(link(g.exit)).toBeVisible();
  });
});

describe("CopyingStep focus", () => {
  it("keeps focus on the button when Pause becomes Resume and back", async () => {
    const user = userEvent.setup();
    const { update } = renderStep();
    // The step takes focus on its next frame, which must not beat this press.
    await waitFor(() => expect(screen.getByRole("heading")).toHaveFocus());
    await user.click(button(strings.copy.pause)!);
    const pressed = document.activeElement;
    update({ state: "paused" });
    expect(button(strings.copy.resume)).toBe(pressed);
    expect(document.activeElement).toBe(pressed);
    update({ state: "running" });
    expect(button(strings.copy.pause)).toBe(pressed);
    expect(document.activeElement).toBe(pressed);
  });

  it("announces the hint when the copy pauses", () => {
    const { update } = renderStep();
    expect(screen.getByRole("status")).toHaveTextContent(g.copying.closeHint);
    const region = screen.getByRole("status");
    update({ state: "paused" });
    expect(screen.getByRole("status")).toBe(region);
    expect(region).toHaveTextContent(g.copying.pausedHint);
  });
});

describe("CopyingStep abort prompt", () => {
  it("is labelled Stop, and its way out says Keep copying", async () => {
    const user = userEvent.setup();
    renderStep();
    await user.click(button(g.copying.stop)!);
    const dialog = await screen.findByRole("alertdialog");
    expect(dialog).toHaveTextContent(strings.copy.abortTitle);
    expect(button(strings.copy.keepCopying)).toBeVisible();
    expect(button(strings.common.cancel)).toBeNull();
  });

  it("closes if the job ends behind it, so it cannot act on a finished job", async () => {
    const user = userEvent.setup();
    const { update, onAbort } = renderStep();
    await user.click(button(g.copying.stop)!);
    await screen.findByRole("alertdialog");
    update({ state: "finished", finishedStatus: "OK" });
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(onAbort).not.toHaveBeenCalled();
  });

  it("stays open across a pause, since the job is still live", async () => {
    const user = userEvent.setup();
    const { update } = renderStep();
    await user.click(button(g.copying.stop)!);
    await screen.findByRole("alertdialog");
    update({ state: "paused" });
    expect(screen.getByRole("alertdialog")).toBeInTheDocument();
  });

  it("with files copied, offers keep and recycle", async () => {
    const user = userEvent.setup();
    const { onAbort } = renderStep();
    await user.click(button(g.copying.stop)!);
    await screen.findByRole("alertdialog");
    expect(button(strings.copy.abortKeepFiles)).toBeInTheDocument();
    await user.click(button(strings.copy.abortRecycleFiles)!);
    expect(onAbort).toHaveBeenCalledWith({ recycle_partial: true });
  });

  it("with nothing copied, offers no recycle and no keep", async () => {
    const user = userEvent.setup();
    const { onAbort } = renderStep({ filesDone: 0 });
    await user.click(button(g.copying.stop)!);
    const dialog = await screen.findByRole("alertdialog");
    expect(dialog).toHaveTextContent(strings.copy.abortConfirm(false));
    expect(button(strings.copy.abortRecycleFiles)).toBeNull();
    expect(button(strings.copy.abortKeepFiles)).toBeNull();
    await user.click(button(strings.copy.abortNothingCopied)!);
    expect(onAbort).toHaveBeenCalledWith({ recycle_partial: false });
  });
});
