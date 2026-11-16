/**
 * Group 5 of the 2026-11-02 review — restoring saved settings and importing a
 * backup say they are under way, and say when they have worked.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";

import { ShellWithPalette } from "@/App";
import { GUIDE_SEEN_KEY } from "@/lib/guideState";
import { libraryPageBaseHandlers } from "@/pages/__tests__/_libraryPageFixtures";
import { config } from "@/pages/__tests__/_settingsPageFixtures";
import { strings } from "@/strings";
import { http, HttpResponse, server } from "@/test/handlers";

function renderAt(path: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <ShellWithPalette />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function heldReply() {
  let finish = () => {};
  const held = new Promise<void>((resolve) => {
    finish = resolve;
  });
  return {
    finish,
    resolver: async () => {
      await held;
      return HttpResponse.json(config);
    },
  };
}

beforeEach(() => {
  // jsdom has no matchMedia, and the shell's Toaster reads it.
  vi.stubGlobal("matchMedia", () => ({
    matches: false,
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
  localStorage.clear();
  localStorage.setItem(GUIDE_SEEN_KEY, "true");
  server.use(
    ...libraryPageBaseHandlers(),
    http.get("/api/help/index", () => HttpResponse.json({ topics: [] })),
    http.get("/api/updates/check", () => HttpResponse.json({})),
    http.get("/api/media/sources", () => HttpResponse.json({ sources: [] })),
    http.get("/api/config/snapshots", () =>
      HttpResponse.json({
        items: [
          {
            id: "snap-1",
            ts: "2026-05-02T16:43:21Z",
            files: ["config.yaml"],
          },
        ],
      }),
    ),
  );
});

describe("Settings", () => {
  it("restoring says it is under way, then that it worked", async () => {
    const reply = heldReply();
    server.use(
      http.post("/api/config/snapshots/snap-1/restore", reply.resolver),
    );
    const user = userEvent.setup();
    renderAt("/settings?tab=snapshots");

    await user.click(
      await screen.findByRole("button", {
        name: strings.settings.snapshotRestoreLabel,
      }),
    );
    await user.click(
      await screen.findByRole("button", {
        name: strings.settings.snapshotRestoreActionLabel(1),
      }),
    );

    expect(await screen.findByText(/restoring your settings/i)).toBeVisible();
    reply.finish();
    expect(
      await screen.findByText(/settings have been restored/i),
    ).toBeVisible();
  });

  it("importing says it is under way, then that it worked", async () => {
    const reply = heldReply();
    server.use(http.post("/api/config/import", reply.resolver));
    const user = userEvent.setup();
    renderAt("/settings?tab=backup");

    await user.upload(
      await screen.findByLabelText(strings.settings.backupImportLabel),
      new File(
        ['{"config":{},"overrides":{},"sessions":{},"notes":{}}'],
        "backup.json",
        { type: "application/json" },
      ),
    );
    await user.click(
      await screen.findByRole("button", {
        name: strings.settings.backupImportActionLabel("backup.json"),
      }),
    );

    expect(await screen.findByText(/importing your settings/i)).toBeVisible();
    reply.finish();
    expect(
      await screen.findByText(/settings have been imported/i),
    ).toBeVisible();
  });
});

describe("Settings backup export", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("names the file by the user's own date and time, not UTC", async () => {
    // Auckland is UTC+12 in May, so the local date differs from UTC's.
    vi.stubEnv("TZ", "Pacific/Auckland");
    server.use(
      http.post("/api/config/export", () =>
        HttpResponse.json({
          config: {},
          overrides: {},
          sessions: {},
          notes: {},
        }),
      ),
    );
    Object.assign(URL, {
      createObjectURL: vi.fn(() => "blob:backup"),
      revokeObjectURL: vi.fn(),
    });
    const names: string[] = [];
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
      this: HTMLAnchorElement,
    ) {
      names.push(this.download);
    });
    const user = userEvent.setup();
    renderAt("/settings?tab=backup");
    const exportButton = await screen.findByRole("button", {
      name: strings.settings.backupExportLabel,
    });

    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-05-02T16:43:21Z"));
    await user.click(exportButton);

    await waitFor(() =>
      expect(names).toEqual(["mame-curator-config-2026-05-03-04-43-21.json"]),
    );
  });
});
