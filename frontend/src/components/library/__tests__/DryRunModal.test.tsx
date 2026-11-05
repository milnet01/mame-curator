import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { DryRunModal } from "../DryRunModal";
import type { DryRunReport } from "@/api/types";

const report: DryRunReport = {
  counts: {
    new: 12,
    replace: 3,
    skip: 5,
    // The server's fields (api/routes/copy.py): every BIOS the games need,
    // and how many of those are not in the ROM folder.
    bios: 2,
    bios_missing_source: 0,
  },
  summary: {},
};

describe("DryRunModal", () => {
  it("renders new / replace / skip counts when open", () => {
    render(
      <DryRunModal
        open
        onOpenChange={() => {}}
        report={report}
        onConfirm={() => {}}
      />,
    );
    expect(screen.getByText(/12 new/)).toBeInTheDocument();
    expect(screen.getByText(/3 replace/)).toBeInTheDocument();
    expect(screen.getByText(/5 skip/)).toBeInTheDocument();
    expect(screen.getByText(/2 BIOS/)).toBeInTheDocument();
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
