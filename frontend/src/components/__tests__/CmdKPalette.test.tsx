import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { CmdKPalette, type CmdKItem } from "../CmdKPalette";

// FP27 A5: dropped 'games' and 'settings' fixture items (the only
// producers in the codebase). The palette now hosts 'actions' + 'help'
// only; fixtures here mirror that.
const items: CmdKItem[] = [
  {
    id: "a1",
    section: "actions",
    label: "Run dry-run",
    value: "action.dryrun",
  },
  {
    id: "a2",
    section: "actions",
    label: "Copy selected",
    value: "action.copy",
  },
  {
    id: "h1",
    section: "help",
    label: "Getting started",
    value: "help.getting-started",
  },
  {
    id: "h2",
    section: "help",
    label: "Keyboard shortcuts",
    value: "help.shortcuts",
  },
];

describe("CmdKPalette", () => {
  it("lists every section when nothing is typed", () => {
    render(
      <CmdKPalette
        open
        onOpenChange={() => {}}
        items={items}
        onSelect={() => {}}
      />,
    );
    expect(screen.getByText("Run dry-run")).toBeInTheDocument();
    expect(screen.getByText("Copy selected")).toBeInTheDocument();
    expect(screen.getByText("Getting started")).toBeInTheDocument();
    expect(screen.getByText("Keyboard shortcuts")).toBeInTheDocument();
  });

  it("filters across sections by typed prefix", async () => {
    const user = userEvent.setup();
    render(
      <CmdKPalette
        open
        onOpenChange={() => {}}
        items={items}
        onSelect={() => {}}
      />,
    );
    await user.type(screen.getByRole("combobox"), "dry");
    expect(screen.getByText("Run dry-run")).toBeInTheDocument();
    expect(screen.queryByText("Copy selected")).toBeNull();
    expect(screen.queryByText("Getting started")).toBeNull();
  });

  it("calls onSelect with the picked item value", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <CmdKPalette
        open
        onOpenChange={() => {}}
        items={items}
        onSelect={onSelect}
      />,
    );
    await user.click(screen.getByText("Copy selected"));
    expect(onSelect).toHaveBeenCalledWith(
      "action.copy",
      expect.objectContaining({ id: "a2" }),
    );
  });

  it("matches when the user types a hint (FP11 § B7)", async () => {
    const user = userEvent.setup();
    const itemsWithHint: CmdKItem[] = [
      ...items,
      {
        id: "a3",
        section: "actions",
        label: "Refresh INIs",
        value: "action.refresh-inis",
        hint: "updates catver, languages, bestgames",
      },
    ];
    render(
      <CmdKPalette
        open
        onOpenChange={() => {}}
        items={itemsWithHint}
        onSelect={() => {}}
      />,
    );
    await user.type(screen.getByRole("combobox"), "catver");
    // The hint text was added to keywords; cmdk should match.
    expect(screen.getByText("Refresh INIs")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// FP27 A5 — CmdK 'games' and 'settings' sections removed
//
// `SECTION_ORDER` at CmdKPalette.tsx:30 declares four sections
// ['games', 'settings', 'actions', 'help'], but zero production code
// produces items with `section: 'games'` or `section: 'settings'` — the
// only producers are these test fixtures (and the strings.cmdK.sections
// catalogue entry).
//
// A5 removes both from four lockstep call-sites: the type union, the
// SECTION_ORDER array, the `grouped` initializer, and the
// `strings.cmdK.sections.{games,settings}` entries in strings.ts.
//
// Pre-fix: SECTION_ORDER contains both → fails. Post-fix: only
// {'actions', 'help'} remain.
// ---------------------------------------------------------------------------

describe("FP27 A5 — CmdK games/settings sections removed", () => {
  it("SECTION_ORDER excludes 'games' and 'settings'", async () => {
    const mod = await import("../CmdKPalette");
    const sectionOrder = (
      mod as unknown as { SECTION_ORDER?: readonly string[] }
    ).SECTION_ORDER;
    // DS04 T3.6: `expect(...).toBeDefined()` surfaces an expected-vs-actual
    // diagnostic if `SECTION_ORDER` ever drops off the export surface,
    // instead of the previous bespoke `throw new Error(...)`.
    expect(sectionOrder).toBeDefined();
    expect(sectionOrder).not.toContain("games");
    expect(sectionOrder).not.toContain("settings");
    expect(new Set(sectionOrder)).toEqual(new Set(["actions", "help"]));
  });

  it("strings.cmdK.sections has no games/settings keys", async () => {
    const { strings } = await import("@/strings");
    const sections = strings.cmdK.sections as Record<string, string>;
    expect(sections).not.toHaveProperty("games");
    expect(sections).not.toHaveProperty("settings");
  });

  // mame-curator-1166: the palette finds pages and help topics, so its
  // button and its box must not promise games or settings.
  it("its button and its box name only pages and help topics", async () => {
    const { strings } = await import("@/strings");
    for (const words of [
      strings.nav.commandPalette,
      strings.cmdK.placeholder,
    ]) {
      expect(words).not.toMatch(/\bgames?\b/i);
      expect(words).not.toMatch(/\bsettings?\b/i);
      expect(words).toMatch(/\bpage\b/i);
      expect(words).toMatch(/\bhelp\b/i);
    }
  });
});

// mame-curator-1160: the palette has no trigger button, so Radix sent focus
// to the page when it closed. It now goes back to where the user was.
describe("CmdKPalette: focus when it closes (mame-curator-1160)", () => {
  function Harness({ withOpener = true }: { withOpener?: boolean }) {
    const [open, setOpen] = useState(false);
    return (
      <>
        <main id="main" tabIndex={-1}>
          {withOpener && (
            <button type="button" onClick={() => setOpen(true)}>
              opener
            </button>
          )}
        </main>
        <CmdKPalette
          open={open}
          onOpenChange={setOpen}
          items={items}
          onSelect={() => {}}
        />
      </>
    );
  }

  it("Escape returns focus to the control that had it", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(screen.getByRole("button", { name: "opener" }));
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
    expect(screen.getByRole("button", { name: "opener" })).toHaveFocus();
  });

  it("choosing an item returns focus too", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(screen.getByRole("button", { name: "opener" }));
    await screen.findByRole("dialog");
    await user.keyboard("{Enter}");
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
    expect(screen.getByRole("button", { name: "opener" })).toHaveFocus();
  });

  it("goes to the page's main area when that control has gone", async () => {
    const user = userEvent.setup();
    const { rerender } = render(<Harness />);
    await user.click(screen.getByRole("button", { name: "opener" }));
    await screen.findByRole("dialog");
    rerender(<Harness withOpener={false} />);
    await user.keyboard("{Escape}");
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
    expect(document.getElementById("main")).toHaveFocus();
  });
});
