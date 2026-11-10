import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { BackupTab } from "../BackupTab";

// DS04 T3.1: removed redundant `afterEach(() => cleanup())` — vitest
// `globals: true` enables RTL's auto-cleanup.

const VALID_BUNDLE_JSON =
  '{"config":{},"overrides":{},"sessions":{},"notes":{}}';

const sampleFile = () =>
  new File([VALID_BUNDLE_JSON], "backup.json", {
    type: "application/json",
  });

describe("BackupTab (FP12 § J + FP13 § B1/B3)", () => {
  it("names no internal phase", () => {
    const { container } = render(
      <BackupTab onExport={() => {}} onImport={() => {}} />,
    );
    expect(container).not.toHaveTextContent(/phase \d/i);
  });

  it("renders Export and Import controls", () => {
    render(<BackupTab onExport={() => {}} onImport={() => {}} />);
    expect(screen.getByRole("button", { name: /^Export/ })).toBeInTheDocument();
    expect(screen.getByLabelText(/^Import/)).toBeInTheDocument();
  });

  it("calls onExport when Export is clicked", async () => {
    const user = userEvent.setup();
    const onExport = vi.fn();
    render(<BackupTab onExport={onExport} onImport={() => {}} />);
    await user.click(screen.getByRole("button", { name: /^Export/ }));
    expect(onExport).toHaveBeenCalledOnce();
  });

  it("opens a confirmation dialog when a valid file is selected", async () => {
    const user = userEvent.setup();
    render(<BackupTab onExport={() => {}} onImport={() => {}} />);
    const input = screen.getByLabelText(/^Import/) as HTMLInputElement;
    await user.upload(input, sampleFile());
    expect(
      screen.getByRole("alertdialog", { name: /replace configuration/i }),
    ).toBeInTheDocument();
  });

  it("uses a concrete action label naming the file (design §8)", async () => {
    const user = userEvent.setup();
    render(<BackupTab onExport={() => {}} onImport={() => {}} />);
    const input = screen.getByLabelText(/^Import/) as HTMLInputElement;
    await user.upload(input, sampleFile());
    expect(
      screen.getByRole("button", { name: "Replace settings from backup.json" }),
    ).toBeInTheDocument();
  });

  it("calls onImport with the parsed bundle only after confirming (FP13 § B1)", async () => {
    const user = userEvent.setup();
    const onImport = vi.fn();
    render(<BackupTab onExport={() => {}} onImport={onImport} />);
    const input = screen.getByLabelText(/^Import/) as HTMLInputElement;
    await user.upload(input, sampleFile());
    expect(onImport).not.toHaveBeenCalled();
    await user.click(
      screen.getByRole("button", { name: "Replace settings from backup.json" }),
    );
    expect(onImport).toHaveBeenCalledExactlyOnceWith({
      config: {},
      overrides: {},
      sessions: {},
      notes: {},
    });
  });

  it("accepts a backup holding picture choices (mame-curator-1146)", async () => {
    const user = userEvent.setup();
    const onImport = vi.fn();
    const pictures = {
      pictures: { pacman: { source: "esde", kind: "title" } },
    };
    const json = JSON.stringify({
      config: {},
      overrides: {},
      sessions: {},
      notes: {},
      pictures,
    });
    render(<BackupTab onExport={() => {}} onImport={onImport} />);
    const input = screen.getByLabelText(/^Import/) as HTMLInputElement;
    await user.upload(input, new File([json], "backup.json"));
    await user.click(
      screen.getByRole("button", { name: "Replace settings from backup.json" }),
    );
    expect(onImport).toHaveBeenCalledWith(
      expect.objectContaining({ pictures }),
    );
  });

  it("does not call onImport when the dialog is cancelled", async () => {
    const user = userEvent.setup();
    const onImport = vi.fn();
    render(<BackupTab onExport={() => {}} onImport={onImport} />);
    const input = screen.getByLabelText(/^Import/) as HTMLInputElement;
    await user.upload(input, sampleFile());
    await user.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onImport).not.toHaveBeenCalled();
  });

  it("renders a parent-supplied error message when error is set", () => {
    render(
      <BackupTab onExport={() => {}} onImport={() => {}} error="Bad bundle." />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(/bad bundle/i);
  });

  it("rejects a file whose JSON parse fails — no dialog opens (FP13 § B1)", async () => {
    const user = userEvent.setup();
    const onImport = vi.fn();
    render(<BackupTab onExport={() => {}} onImport={onImport} />);
    const input = screen.getByLabelText(/^Import/) as HTMLInputElement;
    const garbage = new File(["{ not json"], "garbage.json", {
      type: "application/json",
    });
    await user.upload(input, garbage);
    expect(screen.getByRole("alert")).toHaveTextContent(/not a valid JSON/i);
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(onImport).not.toHaveBeenCalled();
  });

  it("rejects a file whose schema does not match — no dialog opens (FP13 § B1)", async () => {
    const user = userEvent.setup();
    const onImport = vi.fn();
    render(<BackupTab onExport={() => {}} onImport={onImport} />);
    const input = screen.getByLabelText(/^Import/) as HTMLInputElement;
    // Valid JSON but wrong shape (missing required keys + extra key).
    const wrongShape = new File(
      [JSON.stringify({ unrelated: 1 })],
      "wrong.json",
      {
        type: "application/json",
      },
    );
    await user.upload(input, wrongShape);
    expect(screen.getByRole("alert")).toHaveTextContent(
      /not a configuration bundle/i,
    );
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(onImport).not.toHaveBeenCalled();
  });

  it("rejects a file larger than the size cap — no parse, no dialog (FP13 § B3)", async () => {
    const user = userEvent.setup();
    const onImport = vi.fn();
    render(<BackupTab onExport={() => {}} onImport={onImport} />);
    const input = screen.getByLabelText(/^Import/) as HTMLInputElement;
    // DS04 T1.12: stub `File.size` instead of allocating 6 MiB of bytes.
    // The size check is the only thing the cap branch reads — the body
    // never matters — so backing the File with a single-byte payload
    // and forcing a 6 MiB size keeps the assertion semantics identical
    // without burning ~12 MB of jsdom RAM per test run.
    const huge = new File(["x"], "huge.json", { type: "application/json" });
    Object.defineProperty(huge, "size", { value: 6 * 1024 * 1024 });
    await user.upload(input, huge);
    expect(screen.getByRole("alert")).toHaveTextContent(/too large/i);
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(onImport).not.toHaveBeenCalled();
  });

  // Group 5 of the 2026-11-02 review: an import says it is under way, and that it worked.
  it("says an import is under way, and ignores another file", async () => {
    const user = userEvent.setup();
    render(<BackupTab onExport={() => {}} onImport={() => {}} importing />);
    expect(screen.getByRole("status")).toHaveTextContent(/importing/i);

    await user.upload(screen.getByLabelText(/^Import/), sampleFile());
    expect(screen.queryByRole("alertdialog")).toBeNull();
  });

  it("does not open the file chooser while an import is under way", async () => {
    const user = userEvent.setup();
    const choose = vi.spyOn(HTMLInputElement.prototype, "click");
    render(<BackupTab onExport={() => {}} onImport={() => {}} importing />);
    await user.click(screen.getByRole("button", { name: /^Import/ }));
    expect(choose).not.toHaveBeenCalled();
    choose.mockRestore();
  });

  it("says an import worked", () => {
    render(<BackupTab onExport={() => {}} onImport={() => {}} imported />);
    expect(screen.getByRole("status")).toHaveTextContent(/imported/i);
  });

  it("drops the success words once something newer has failed", () => {
    render(
      <BackupTab
        onExport={() => {}}
        onImport={() => {}}
        imported
        error="Could not export configuration."
      />,
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.queryByRole("status")).toBeNull();
  });
});
