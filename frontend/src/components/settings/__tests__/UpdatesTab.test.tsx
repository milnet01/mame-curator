import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { UpdatesTab, type UpdateActions } from "../UpdatesTab";
import type { AppUpdateInfo } from "@/api/types";

// mame-curator-1010 §4.7 — the Updates tab's actions per install kind, the
// What's new modal and the INI preview's lists.

const updates = {
  channel: "stable" as const,
  check_on_startup: true,
  ini_check_on_startup: true,
};

function info(fields: Partial<AppUpdateInfo> = {}): AppUpdateInfo {
  return {
    current_version: "1.3.0",
    latest_version: "1.4.0",
    update_available: true,
    install_kind: "git",
    can_apply: true,
    notes_html: "<h2>Added</h2><p>A new thing</p>",
    release_url: "https://example.test/v1.4.0",
    check_error: null,
    restart_pending: false,
    rollback_available: false,
    ...fields,
  };
}

function actions(fields: Partial<UpdateActions> = {}): UpdateActions {
  return {
    onCheckNow: vi.fn(),
    checking: false,
    onApply: vi.fn(),
    applying: false,
    onRollback: vi.fn(),
    rollingBack: false,
    onIniPreview: vi.fn(),
    iniPreviewing: false,
    onIniApply: vi.fn(),
    iniApplying: false,
    iniApplied: false,
    ...fields,
  };
}

function renderTab(i: AppUpdateInfo, a: UpdateActions) {
  render(
    <UpdatesTab
      updates={updates}
      onChange={() => {}}
      updateInfo={i}
      actions={a}
    />,
  );
}

describe("UpdatesTab (mame-curator-1010)", () => {
  it("offers Update on a git clone and calls apply", async () => {
    const a = actions();
    renderTab(info(), a);
    await userEvent.click(screen.getByRole("button", { name: "Update" }));
    expect(a.onApply).toHaveBeenCalledOnce();
  });

  it("offers a download on a bundle and says where it landed", () => {
    renderTab(
      info({ install_kind: "bundle" }),
      actions({
        applyResult: {
          install_kind: "bundle",
          from_version: "1.3.0",
          to_version: "1.4.0",
          rolled_back: false,
          sync_failed: false,
          restart_required: false,
          snapshot_id: null,
          downloaded_path: "/apps/MAME_Curator-1.4.0-x86_64.AppImage",
          output: null,
        },
      }),
    );
    expect(
      screen.getByRole("button", { name: "Download update" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/MAME_Curator-1\.4\.0/)).toBeInTheDocument();
  });

  it("links the release page on a package install instead of a button", () => {
    renderTab(info({ install_kind: "package", can_apply: false }), actions());
    expect(screen.queryByRole("button", { name: /update/i })).toBeNull();
    expect(screen.getByRole("link", { name: /release page/i })).toHaveAttribute(
      "href",
      "https://example.test/v1.4.0",
    );
  });

  it("asks for a restart instead of offering the update again", () => {
    renderTab(
      info({ restart_pending: true, rollback_available: true }),
      actions(),
    );
    expect(screen.queryByRole("button", { name: "Update" })).toBeNull();
    expect(screen.getByText(/restart mame curator/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Roll back" }),
    ).toBeInTheDocument();
  });

  it("opens What's new with the sanitized notes", async () => {
    renderTab(
      info({ notes_html: '<h2>Added</h2><img src="x" onerror="alert(1)">' }),
      actions(),
    );
    await userEvent.click(screen.getByRole("button", { name: "What's new" }));
    const dialog = screen.getByRole("dialog");
    expect(
      within(dialog).getByRole("heading", { name: "Added" }),
    ).toBeInTheDocument();
    expect(dialog.innerHTML).not.toContain("onerror");
  });

  it("shows the check error when the check failed", () => {
    renderTab(
      info({
        latest_version: null,
        update_available: false,
        can_apply: false,
        notes_html: null,
        check_error: "GitHub answered 403",
      }),
      actions(),
    );
    expect(screen.getByText(/GitHub answered 403/)).toBeInTheDocument();
  });

  it("lists the games an INI preview would add and remove, then applies", async () => {
    const a = actions({
      iniPreview: {
        changed_files: ["mature.ini"],
        failed: [["series.ini", "https://ini.test/series.ini"]],
        winners_added: ["dkong"],
        winners_removed: ["pacman", "galaga"],
      },
    });
    renderTab(info(), a);
    expect(
      screen.getByText(/would join the library \(1\)/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/would leave the library \(2\)/),
    ).toBeInTheDocument();
    expect(screen.getByText("galaga")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "https://ini.test/series.ini" }),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Apply" }));
    expect(a.onIniApply).toHaveBeenCalledOnce();
  });

  it("offers no Apply when the preview found nothing new", () => {
    renderTab(
      info(),
      actions({
        iniPreview: {
          changed_files: [],
          failed: [],
          winners_added: [],
          winners_removed: [],
        },
      }),
    );
    expect(screen.getByText(/already up to date/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Apply" })).toBeNull();
  });
});
