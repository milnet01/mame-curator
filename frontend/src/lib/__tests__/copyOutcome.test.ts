/**
 * mame-curator-1241 (RR-10-6) — the reading both copy screens share.
 */
import { describe, expect, it } from "vitest";
import type { CopyModalState } from "@/components/library/CopyModal";
import { copyView } from "@/lib/copyOutcome";
import { strings } from "@/strings";

const base: CopyModalState = {
  jobId: "j1",
  state: "running",
  filesDone: 2,
  filesTotal: 4,
  bytesDone: 0,
  bytesTotal: 0,
  currentFile: "pacman.zip",
  warnings: [],
};

describe("copyView", () => {
  it("a finish says 100 though skipped games left files undone", () => {
    const view = copyView({ ...base, state: "finished", finishedStatus: "OK" });
    expect(view.outcome).toBe("complete");
    expect(view.pct).toBe(100);
    expect(view.live).toBe(false);
  });

  it("a running copy says how far it is", () => {
    const view = copyView(base);
    expect(view.pct).toBe(50);
    expect(view.progressText).toBe(
      strings.copy.progressLine(2, 4, "pacman.zip"),
    );
  });

  it("says it is preparing until the total arrives, not 0 / 0", () => {
    const view = copyView({ ...base, filesDone: 0, filesTotal: 0 });
    expect(view.pct).toBe(0);
    expect(view.progressText).toBe(strings.copy.preparing);
  });

  it.each([
    ["running", false, true],
    ["paused", true, true],
    ["terminating", false, false],
  ] as const)(
    "%s: paused %s, controllable %s",
    (state, paused, controllable) => {
      const view = copyView({ ...base, state });
      expect(view.live).toBe(true);
      expect(view.paused).toBe(paused);
      expect(view.controllable).toBe(controllable);
    },
  );
});
