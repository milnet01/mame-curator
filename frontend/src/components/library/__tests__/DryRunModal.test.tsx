import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { DryRunModal } from "../DryRunModal";
import type { DryRunReport } from "@/api/types";

// The server's fields (api/routes/copy.py dry_run). mame-curator-1198: the
// modal read `replace` and `skip`, which the server never sends.
const report: DryRunReport = {
  counts: {
    selected: 21,
    new: 12,
    already_copied: 4,
    missing_source: 5,
    not_in_playlist: 1,
    // Every BIOS the games need, and how many are not in the ROM folder.
    bios: 2,
    bios_missing_source: 0,
  },
  summary: {},
};

describe("DryRunModal", () => {
  it("renders the counts the server sends, in plain words", () => {
    render(
      <DryRunModal
        open
        onOpenChange={() => {}}
        report={report}
        onConfirm={() => {}}
      />,
    );
    expect(screen.getByText("12 new")).toBeInTheDocument();
    expect(screen.getByText("4 already there")).toBeInTheDocument();
    expect(
      screen.getByText("5 missing from your ROM folder"),
    ).toBeInTheDocument();
    expect(screen.getByText("1 not in your game list")).toBeInTheDocument();
    expect(screen.getByText("2 BIOS included")).toBeInTheDocument();
  });

  it("counts only the BIOS files it can copy, and names the missing ones", () => {
    // mame-curator-1163: the modal read a field the server never sends.
    render(
      <DryRunModal
        open
        onOpenChange={() => {}}
        report={{
          ...report,
          counts: { ...report.counts, bios: 3, bios_missing_source: 1 },
        }}
        onConfirm={() => {}}
      />,
    );
    expect(screen.getByText("2 BIOS included")).toBeInTheDocument();
    expect(
      screen.getByText(
        /1 BIOS file these games need is not in your ROM folder/,
      ),
    ).toBeInTheDocument();
  });

  it("says nothing about missing BIOS files when none are missing", () => {
    render(
      <DryRunModal
        open
        onOpenChange={() => {}}
        report={report}
        onConfirm={() => {}}
      />,
    );
    expect(
      screen.queryByText(/not in your ROM folder/),
    ).not.toBeInTheDocument();
  });

  it("does not render when closed", () => {
    render(
      <DryRunModal
        open={false}
        onOpenChange={() => {}}
        report={report}
        onConfirm={() => {}}
      />,
    );
    expect(screen.queryByText(/12 new/)).not.toBeInTheDocument();
  });

  it("calls onConfirm when the confirm button is clicked", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(
      <DryRunModal
        open
        onOpenChange={() => {}}
        report={report}
        onConfirm={onConfirm}
      />,
    );
    await user.click(screen.getByRole("button", { name: /^copy/i }));
    expect(onConfirm).toHaveBeenCalledOnce();
  });
});
