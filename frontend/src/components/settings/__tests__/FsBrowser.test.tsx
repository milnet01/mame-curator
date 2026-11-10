import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { FsBrowser } from "../FsBrowser";
import { strings } from "@/strings";
import {
  server,
  http,
  HttpResponse,
  makeSandboxedListHandler,
} from "@/test/handlers";

// DS04 T3.1: removed redundant `afterEach(() => cleanup())` — vitest
// `globals: true` enables RTL's auto-cleanup.

const HOME = "/home/test";
const SUB = "/home/test/projects";

const homeListing = {
  path: HOME,
  parent: null,
  entries: [
    {
      name: "projects",
      path: SUB,
      is_dir: true,
      hidden: false,
      size: null,
      mtime: "2026-05-01T00:00:00Z",
    },
    {
      name: "notes.txt",
      path: "/home/test/notes.txt",
      is_dir: false,
      hidden: false,
      size: 42,
      mtime: "2026-05-01T00:00:00Z",
    },
  ],
};

const subListing = {
  path: SUB,
  parent: HOME,
  entries: [
    {
      name: "mame",
      path: "/home/test/projects/mame",
      is_dir: true,
      hidden: false,
      size: null,
      mtime: "2026-05-01T00:00:00Z",
    },
  ],
};

beforeEach(() => {
  server.use(
    http.get("/api/fs/home", () => HttpResponse.json({ path: HOME })),
    http.get("/api/fs/roots", () => HttpResponse.json({ roots: ["/"] })),
    http.get("/api/fs/allowed-roots", () =>
      HttpResponse.json({
        roots: [{ id: "r1", path: HOME, source: "config" }],
      }),
    ),
    http.get("/api/fs/list", ({ request }) => {
      const path = new URL(request.url).searchParams.get("path");
      if (path === HOME) return HttpResponse.json(homeListing);
      if (path === SUB) return HttpResponse.json(subListing);
      return HttpResponse.json(
        {
          code: "fs_sandboxed",
          detail: `${path} is outside the allowlist`,
          fields: [],
        },
        { status: 403 },
      );
    }),
  );
});

function renderWithClient(ui: React.ReactElement) {
  // Disable retry for BOTH queries and mutations — the grant test fires a
  // POST mutation that would otherwise inherit the 3× default retry and
  // mask a failing handler behind a retry-success.
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("FsBrowser (FP12 § G)", () => {
  it("does not render OR fetch when open=false (mame-curator-1047)", async () => {
    // mame-curator-1047: the fs queries are gated on `open` (enabled: open),
    // so a closed FsBrowser mounted on the Settings page issues ZERO fs
    // requests. Pre-fix, the useQuery hooks fired on mount regardless of
    // `open`, prefetching home / roots / allowed-roots for a dialog the user
    // never opened. A request:start spy is the regression lock.
    const fsRequests: string[] = [];
    const onRequest = ({ request }: { request: Request }) => {
      const { pathname } = new URL(request.url);
      if (pathname.startsWith("/api/fs")) fsRequests.push(pathname);
    };
    server.events.on("request:start", onRequest);
    try {
      renderWithClient(
        <FsBrowser open={false} onOpenChange={() => {}} onPick={() => {}} />,
      );
      // Flush any mount-effect query kick-off; gated queries fire nothing.
      await new Promise((resolve) => setTimeout(resolve, 0));
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
      expect(fsRequests).toEqual([]);
    } finally {
      server.events.removeListener("request:start", onRequest);
    }
  });

  it("lists the home directory on first open", async () => {
    renderWithClient(
      <FsBrowser open onOpenChange={() => {}} onPick={() => {}} />,
    );
    expect(await screen.findByText("projects")).toBeInTheDocument();
  });

  it("navigates into a directory when clicked", async () => {
    const user = userEvent.setup();
    renderWithClient(
      <FsBrowser open onOpenChange={() => {}} onPick={() => {}} />,
    );
    await user.click(await screen.findByText("projects"));
    expect(await screen.findByText("mame")).toBeInTheDocument();
  });

  it("returns to the parent via Up", async () => {
    const user = userEvent.setup();
    renderWithClient(
      <FsBrowser open onOpenChange={() => {}} onPick={() => {}} />,
    );
    await user.click(await screen.findByText("projects"));
    await screen.findByText("mame");
    await user.click(screen.getByRole("button", { name: /up/i }));
    expect(await screen.findByText("projects")).toBeInTheDocument();
  });

  it("calls onPick with the current path when Use this folder is clicked", async () => {
    const user = userEvent.setup();
    const onPick = vi.fn();
    renderWithClient(
      <FsBrowser open onOpenChange={() => {}} onPick={onPick} />,
    );
    await screen.findByText("projects");
    await user.click(screen.getByRole("button", { name: /use this folder/i }));
    expect(onPick).toHaveBeenCalledExactlyOnceWith(HOME);
  });

  it("hides files in directory mode (default)", async () => {
    renderWithClient(
      <FsBrowser open onOpenChange={() => {}} onPick={() => {}} />,
    );
    await screen.findByText("projects");
    expect(screen.queryByText("notes.txt")).not.toBeInTheDocument();
  });

  it("shows and selects files in file mode", async () => {
    const user = userEvent.setup();
    const onPick = vi.fn();
    renderWithClient(
      <FsBrowser open onOpenChange={() => {}} onPick={onPick} mode="file" />,
    );
    const fileEntry = await screen.findByText("notes.txt");
    await user.click(fileEntry);
    expect(onPick).toHaveBeenCalledExactlyOnceWith("/home/test/notes.txt");
  });

  it("closes via the Cancel button", async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    renderWithClient(
      <FsBrowser open onOpenChange={onOpenChange} onPick={() => {}} />,
    );
    await screen.findByText("projects");
    await user.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("surfaces a grant prompt when listing returns fs_sandboxed", async () => {
    server.use(makeSandboxedListHandler(HOME, homeListing));
    renderWithClient(
      <FsBrowser
        open
        onOpenChange={() => {}}
        onPick={() => {}}
        initialPath="/etc"
      />,
    );
    await waitFor(() =>
      expect(
        screen.getByRole("alertdialog", {
          name: /allow mame curator to look here/i,
        }),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByRole("button", { name: "Allow /etc" }),
    ).toBeInTheDocument();
  });

  it('hides the "Use this folder" footer button in file mode (FP13 § C3)', async () => {
    renderWithClient(
      <FsBrowser open onOpenChange={() => {}} onPick={() => {}} mode="file" />,
    );
    await screen.findByText("projects");
    expect(
      screen.queryByRole("button", { name: /use this folder/i }),
    ).not.toBeInTheDocument();
  });

  it("does not render a drive-root button that duplicates an allowed root (FP13 § C4)", async () => {
    server.use(
      http.get("/api/fs/roots", () =>
        HttpResponse.json({ roots: ["/", HOME] }),
      ),
    );
    renderWithClient(
      <FsBrowser open onOpenChange={() => {}} onPick={() => {}} />,
    );
    await screen.findByText("projects");
    // HOME is in allowed-roots; only one quick-jump button for HOME exists.
    const homeButtons = screen.getAllByRole("button", { name: HOME });
    expect(homeButtons).toHaveLength(1);
    // The other drive root '/' still renders.
    expect(screen.getByRole("button", { name: "/" })).toBeInTheDocument();
  });

  it("renders ONLY the grant prompt when sandbox-blocked (not co-mounted with browse Dialog)", async () => {
    /**
     * FP20-K: previously both the outer picker Dialog and the
     * grant ConfirmationDialog were rendered as siblings of a fragment.
     * ``Esc`` in the grant prompt then fired BOTH dialogs' onOpenChange
     * handlers — the outer Dialog's handler calls the parent's
     * onOpenChange(false) directly, unmounting FsBrowser even though
     * the user only intended to dismiss the grant prompt.
     *
     * Fix: render only one layer at a time. When ``sandboxBlocked`` is
     * truthy, the browse Dialog is unmounted and the AlertDialog is the
     * sole open layer; Esc routes cleanly to a single handler. The
     * FP13 § C2 behaviour (cancelling the grant closes FsBrowser) is
     * preserved by the AlertDialog's own onOpenChange.
     */
    server.use(makeSandboxedListHandler(HOME, homeListing));
    renderWithClient(
      <FsBrowser
        open
        onOpenChange={() => {}}
        onPick={() => {}}
        initialPath="/etc"
      />,
    );
    await screen.findByRole("alertdialog", {
      name: /allow mame curator to look here/i,
    });
    // The outer browse Dialog's title is the canonical signal that it
    // is in the DOM. If both dialogs were co-mounted (pre-FP20-K), the
    // text would be present on the queryable surface.
    expect(
      screen.queryByText(strings.settings.fsBrowserTitle),
    ).not.toBeInTheDocument();
    // And only one dialog/alertdialog should be in the DOM.
    expect(screen.queryAllByRole("dialog")).toHaveLength(0);
    expect(screen.queryAllByRole("alertdialog")).toHaveLength(1);
  });

  it("closes the modal when the grant prompt is cancelled (FP13 § C2)", async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    server.use(makeSandboxedListHandler(HOME, homeListing));
    renderWithClient(
      <FsBrowser
        open
        onOpenChange={onOpenChange}
        onPick={() => {}}
        initialPath="/etc"
      />,
    );
    await screen.findByRole("alertdialog", {
      name: /allow mame curator to look here/i,
    });
    // The grant prompt offers Cancel + the "Allow /etc" affirm.
    // Clicking Cancel must close FsBrowser entirely, not silently reset to
    // home (which would re-open the prompt if home hadn't loaded).
    await user.click(screen.getByRole("button", { name: /^cancel$/i }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("surfaces an inline error when home detection fails (FP13 § C7)", async () => {
    server.use(
      http.get("/api/fs/home", () =>
        HttpResponse.json(
          { code: "fs_path_invalid", detail: "no home", fields: [] },
          { status: 500 },
        ),
      ),
    );
    renderWithClient(
      <FsBrowser open onOpenChange={() => {}} onPick={() => {}} />,
    );
    expect(
      await screen.findByText(/your home folder could not be found/i),
    ).toBeInTheDocument();
  });

  it("POSTs a grant when the prompt is confirmed", async () => {
    const user = userEvent.setup();
    let granted: string | null = null;
    server.use(
      makeSandboxedListHandler(HOME, homeListing),
      http.post("/api/fs/allowed-roots", async ({ request }) => {
        const body = (await request.json()) as { path: string };
        granted = body.path;
        return HttpResponse.json({
          roots: [
            { id: "r1", path: HOME, source: "config" },
            { id: "r2", path: body.path, source: "granted" },
          ],
        });
      }),
    );
    renderWithClient(
      <FsBrowser
        open
        onOpenChange={() => {}}
        onPick={() => {}}
        initialPath="/etc"
      />,
    );
    const grantBtn = await screen.findByRole("button", {
      name: "Allow /etc",
    });
    await user.click(grantBtn);
    await waitFor(() => expect(granted).toBe("/etc"));
  });

  // mame-curator-1145 INV-12.
  it("keeps the picker open on a folder the user allows", async () => {
    const user = userEvent.setup();
    let granted = false;
    server.use(
      http.get("/api/fs/list", ({ request }) => {
        if (!granted) {
          return HttpResponse.json(
            { code: "fs_sandboxed", detail: "outside", fields: [] },
            { status: 403 },
          );
        }
        const path = new URL(request.url).searchParams.get("path");
        return HttpResponse.json({ path, parent: null, entries: [] });
      }),
      http.post("/api/fs/allowed-roots", () => {
        granted = true;
        return HttpResponse.json({ roots: [] });
      }),
    );
    const onOpenChange = vi.fn();
    renderWithClient(
      <FsBrowser
        open
        onOpenChange={onOpenChange}
        onPick={() => {}}
        initialPath="/mnt/games"
      />,
    );
    await user.click(
      await screen.findByRole("button", { name: "Allow /mnt/games" }),
    );
    expect(
      await screen.findByRole("button", {
        name: strings.settings.fsBrowserUseDirectory,
      }),
    ).toBeInTheDocument();
    expect(onOpenChange).not.toHaveBeenCalledWith(false);
  });

  it("names what it is choosing by mode", async () => {
    const { unmount } = renderWithClient(
      <FsBrowser open onOpenChange={() => {}} onPick={() => {}} />,
    );
    expect(
      await screen.findByRole("dialog", {
        name: strings.settings.fsBrowserTitle,
      }),
    ).toBeInTheDocument();
    unmount();
    renderWithClient(
      <FsBrowser open onOpenChange={() => {}} onPick={() => {}} mode="file" />,
    );
    expect(
      await screen.findByRole("dialog", {
        name: strings.settings.fsBrowserTitleFile,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(strings.settings.fsBrowserDescriptionFile),
    ).toBeInTheDocument();
  });

  it("large makes its rows, buttons, words and grant prompt large", async () => {
    const { unmount } = renderWithClient(
      <FsBrowser open onOpenChange={() => {}} onPick={() => {}} large />,
    );
    const row = await screen.findByRole("button", { name: /projects/ });
    expect(row).toHaveClass("text-xl", "min-h-12");
    expect(
      screen.getByRole("button", { name: strings.settings.fsBrowserHome }),
    ).toHaveClass("text-xl", "min-h-12");
    expect(screen.getByText(strings.settings.fsBrowserDescription)).toHaveClass(
      "text-xl",
    );
    unmount();

    server.use(makeSandboxedListHandler(HOME, homeListing));
    renderWithClient(
      <FsBrowser
        open
        onOpenChange={() => {}}
        onPick={() => {}}
        initialPath="/etc"
        large
      />,
    );
    expect(
      await screen.findByRole("button", { name: "Allow /etc" }),
    ).toHaveClass("text-xl", "min-h-12");
    expect(
      screen.getByText(strings.settings.fsGrantConfirm("/etc")),
    ).toHaveClass("text-xl");
  });

  it("without large keeps today's sizes", async () => {
    renderWithClient(
      <FsBrowser open onOpenChange={() => {}} onPick={() => {}} />,
    );
    const row = await screen.findByRole("button", { name: /projects/ });
    expect(row).toHaveClass("text-sm");
    expect(row).not.toHaveClass("text-xl");
  });

  // mame-curator-1145 INV-12: a new user sees only what they need.
  it("simple leaves out hidden folders and the app's own, and keeps the rest", async () => {
    server.use(
      http.get("/api/fs/roots", () => HttpResponse.json({ roots: ["/"] })),
      http.get("/api/fs/allowed-roots", () =>
        HttpResponse.json({
          roots: [
            { id: "a", path: "/data/app-folder", source: "config" },
            { id: "b", path: "/mnt/granted", source: "granted" },
          ],
        }),
      ),
      http.get("/api/fs/list", () =>
        HttpResponse.json({
          ...homeListing,
          entries: [
            ...homeListing.entries,
            {
              ...homeListing.entries[0],
              name: ".cache",
              path: "/h/.cache",
              hidden: true,
            },
          ],
        }),
      ),
    );
    const { unmount } = renderWithClient(
      <FsBrowser open onOpenChange={() => {}} onPick={() => {}} simple />,
    );
    await screen.findByRole("button", { name: /^projects/ });
    expect(
      screen.getByRole("button", { name: "/mnt/granted" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "/" })).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "/data/app-folder" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /^\.cache/ }),
    ).not.toBeInTheDocument();
    unmount();

    renderWithClient(
      <FsBrowser open onOpenChange={() => {}} onPick={() => {}} />,
    );
    expect(
      await screen.findByRole("button", { name: /^\.cache/ }),
    ).toBeInTheDocument();
    expect(
      await screen.findByRole("button", { name: "/data/app-folder" }),
    ).toBeInTheDocument();
  });

  it("large scrolls rather than run off the window", async () => {
    renderWithClient(
      <FsBrowser open onOpenChange={() => {}} onPick={() => {}} large />,
    );
    expect(await screen.findByRole("dialog")).toHaveClass("overflow-y-auto");
  });

  describe("mame-curator-1145 review: what simple hides", () => {
    const listingOf = (...entries: object[]) =>
      http.get("/api/fs/list", () =>
        HttpResponse.json({ path: HOME, parent: null, entries }),
      );
    const row = (name: string, is_dir: boolean, hidden = false) => ({
      name,
      path: `${HOME}/${name}`,
      is_dir,
      hidden,
      size: is_dir ? null : 1,
      mtime: "2026-05-01T00:00:00Z",
    });

    it("goes by the server's hidden, so a system's own mark counts", async () => {
      server.use(
        listingOf(row("AppData", true, true), row("Games", true, false)),
      );
      renderWithClient(
        <FsBrowser open onOpenChange={() => {}} onPick={() => {}} simple />,
      );
      await screen.findByRole("button", { name: /^Games/ });
      expect(
        screen.queryByRole("button", { name: /^AppData/ }),
      ).not.toBeInTheDocument();
    });

    it("hides folders only: a dot-file stays in file mode", async () => {
      server.use(
        listingOf(row(".hidden.dat", false, true), row(".cache", true, true)),
      );
      renderWithClient(
        <FsBrowser
          open
          onOpenChange={() => {}}
          onPick={() => {}}
          simple
          mode="file"
        />,
      );
      expect(
        await screen.findByRole("button", { name: ".hidden.dat" }),
      ).toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: /^\.cache/ }),
      ).not.toBeInTheDocument();
    });

    it("keeps a drive that is also a root simple leaves out", async () => {
      server.use(
        http.get("/api/fs/roots", () => HttpResponse.json({ roots: ["D:\\"] })),
        http.get("/api/fs/allowed-roots", () =>
          HttpResponse.json({
            roots: [{ id: "a", path: "D:\\", source: "config" }],
          }),
        ),
      );
      renderWithClient(
        <FsBrowser open onOpenChange={() => {}} onPick={() => {}} simple />,
      );
      await screen.findByRole("button", { name: /^projects/ });
      expect(
        await screen.findByRole("button", { name: "D:\\" }),
      ).toBeInTheDocument();
    });

    it("says a folder of files holds only files, not that it is empty", async () => {
      server.use(listingOf(row("a.zip", false), row("b.zip", false)));
      renderWithClient(
        <FsBrowser open onOpenChange={() => {}} onPick={() => {}} />,
      );
      expect(
        await screen.findByText(strings.settings.fsBrowserOnlyFiles),
      ).toBeInTheDocument();
      expect(
        screen.queryByText(strings.settings.fsBrowserNoFolders),
      ).not.toBeInTheDocument();
    });

    it("says no folders where there is nothing, by mode", async () => {
      server.use(listingOf());
      const { unmount } = renderWithClient(
        <FsBrowser open onOpenChange={() => {}} onPick={() => {}} />,
      );
      expect(
        await screen.findByText(strings.settings.fsBrowserNoFolders),
      ).toBeInTheDocument();
      unmount();
      renderWithClient(
        <FsBrowser
          open
          onOpenChange={() => {}}
          onPick={() => {}}
          mode="file"
        />,
      );
      expect(
        await screen.findByText(strings.settings.fsBrowserEmpty),
      ).toBeInTheDocument();
    });

    it("says only-files too when simple has hidden the only folders", async () => {
      server.use(listingOf(row(".cache", true, true), row("a.zip", false)));
      renderWithClient(
        <FsBrowser open onOpenChange={() => {}} onPick={() => {}} simple />,
      );
      expect(
        await screen.findByText(strings.settings.fsBrowserOnlyFiles),
      ).toBeInTheDocument();
    });
  });

  describe("mame-curator-1145 review: a folder that has not opened", () => {
    const failing = (status: number, code: string) =>
      http.get("/api/fs/list", () =>
        HttpResponse.json({ code, detail: "no", fields: [] }, { status }),
      );
    const useButton = () =>
      screen.getByRole("button", {
        name: strings.settings.fsBrowserUseDirectory,
      });

    it("cannot be chosen when it failed to open", async () => {
      server.use(failing(404, "fs_not_found"));
      renderWithClient(
        <FsBrowser
          open
          onOpenChange={() => {}}
          onPick={() => {}}
          initialPath="/gone"
        />,
      );
      await screen.findByText(strings.settings.fsBrowserListError);
      expect(useButton()).toBeDisabled();
    });

    it("cannot be chosen while it is loading", async () => {
      server.use(http.get("/api/fs/list", () => new Promise(() => {})));
      renderWithClient(
        <FsBrowser
          open
          onOpenChange={() => {}}
          onPick={() => {}}
          initialPath="/slow"
        />,
      );
      await screen.findByText(strings.settings.fsBrowserLoading);
      expect(useButton()).toBeDisabled();
    });

    it("says nothing about its contents before home is known", async () => {
      server.use(http.get("/api/fs/home", () => new Promise(() => {})));
      renderWithClient(
        <FsBrowser open onOpenChange={() => {}} onPick={() => {}} />,
      );
      await screen.findByRole("dialog");
      await new Promise((resolve) => setTimeout(resolve, 20));
      expect(
        screen.queryByText(strings.settings.fsBrowserNoFolders),
      ).not.toBeInTheDocument();
      expect(screen.queryByRole("list")).not.toBeInTheDocument();
    });

    it("says nothing about its contents when home failed", async () => {
      server.use(
        http.get("/api/fs/home", () =>
          HttpResponse.json(
            { code: "fs_path_invalid", detail: "no", fields: [] },
            { status: 500 },
          ),
        ),
      );
      renderWithClient(
        <FsBrowser open onOpenChange={() => {}} onPick={() => {}} />,
      );
      await screen.findByText(/your home folder could not be found/i);
      expect(
        screen.queryByText(strings.settings.fsBrowserNoFolders),
      ).not.toBeInTheDocument();
      expect(screen.queryByRole("list")).not.toBeInTheDocument();
    });

    it("says Already at the top only at the top", async () => {
      const up = () =>
        screen.getByRole("button", { name: strings.settings.fsBrowserUp });
      server.use(failing(404, "fs_not_found"));
      const { unmount } = renderWithClient(
        <FsBrowser
          open
          onOpenChange={() => {}}
          onPick={() => {}}
          initialPath="/gone"
        />,
      );
      await screen.findByText(strings.settings.fsBrowserListError);
      expect(up()).not.toHaveAttribute("title");
      unmount();

      server.resetHandlers();
      server.use(
        http.get("/api/fs/home", () => HttpResponse.json({ path: HOME })),
        http.get("/api/fs/roots", () => HttpResponse.json({ roots: [] })),
        http.get("/api/fs/allowed-roots", () =>
          HttpResponse.json({ roots: [] }),
        ),
        http.get("/api/fs/list", () => HttpResponse.json(homeListing)),
      );
      renderWithClient(
        <FsBrowser open onOpenChange={() => {}} onPick={() => {}} />,
      );
      await screen.findByRole("button", { name: /^projects/ });
      expect(up()).toHaveAttribute("title", strings.settings.fsBrowserUpAtTop);
    });
  });

  describe("mame-curator-1145 review: the grant prompt", () => {
    it("sends one grant for a double press, and says it is busy", async () => {
      let posts = 0;
      let answer: () => void = () => {};
      server.use(
        makeSandboxedListHandler(HOME, homeListing),
        http.post("/api/fs/allowed-roots", async () => {
          posts += 1;
          await new Promise<void>((resolve) => {
            answer = resolve;
          });
          return HttpResponse.json({ roots: [] });
        }),
      );
      renderWithClient(
        <FsBrowser
          open
          onOpenChange={() => {}}
          onPick={() => {}}
          initialPath="/etc"
        />,
      );
      const allow = await screen.findByRole("button", { name: "Allow /etc" });
      // Faster than the page can say it is busy.
      fireEvent.click(allow);
      fireEvent.click(allow);
      await waitFor(() =>
        expect(allow).toHaveAttribute("aria-disabled", "true"),
      );
      expect(screen.getByRole("button", { name: /^cancel$/i })).toHaveAttribute(
        "aria-disabled",
        "true",
      );
      await waitFor(() => expect(posts).toBe(1));
      answer();
    });

    it("cannot be left by Esc or Cancel during the grant", async () => {
      const user = userEvent.setup();
      let answer: () => void = () => {};
      server.use(
        makeSandboxedListHandler(HOME, homeListing),
        http.post("/api/fs/allowed-roots", async () => {
          await new Promise<void>((resolve) => {
            answer = resolve;
          });
          return HttpResponse.json({ roots: [] });
        }),
      );
      const onOpenChange = vi.fn();
      renderWithClient(
        <FsBrowser
          open
          onOpenChange={onOpenChange}
          onPick={() => {}}
          initialPath="/etc"
        />,
      );
      const allow = await screen.findByRole("button", { name: "Allow /etc" });
      await user.click(allow);
      await waitFor(() => expect(allow).toHaveAttribute("aria-disabled"));
      await user.keyboard("{Escape}");
      await user.click(screen.getByRole("button", { name: /^cancel$/i }));
      expect(onOpenChange).not.toHaveBeenCalledWith(false);
      answer();
    });
  });

  describe("mame-curator-1145 review: large and long", () => {
    it("large has no small X, and normal keeps it", async () => {
      const { unmount } = renderWithClient(
        <FsBrowser open onOpenChange={() => {}} onPick={() => {}} large />,
      );
      await screen.findByRole("dialog");
      expect(
        screen.queryByRole("button", { name: "Close" }),
      ).not.toBeInTheDocument();
      unmount();
      renderWithClient(
        <FsBrowser open onOpenChange={() => {}} onPick={() => {}} />,
      );
      await screen.findByRole("dialog");
      expect(screen.getByRole("button", { name: "Close" })).toBeInTheDocument();
    });

    it("shows the whole path in large, and offers it as a title in normal", async () => {
      const { unmount } = renderWithClient(
        <FsBrowser open onOpenChange={() => {}} onPick={() => {}} large />,
      );
      await screen.findByRole("button", { name: /^projects/ });
      const largeLine = screen.getByText(HOME, { selector: "code" });
      expect(largeLine).not.toHaveClass("truncate");
      unmount();
      renderWithClient(
        <FsBrowser open onOpenChange={() => {}} onPick={() => {}} />,
      );
      await screen.findByRole("button", { name: /^projects/ });
      expect(screen.getByText(HOME, { selector: "code" })).toHaveAttribute(
        "title",
        HOME,
      );
    });
  });

  describe("mame-curator-1145 review: listings", () => {
    it("asks again each time a folder is opened", async () => {
      let asked = 0;
      server.use(
        http.get("/api/fs/list", () => {
          asked += 1;
          return HttpResponse.json(homeListing);
        }),
      );
      const qc = new QueryClient({
        defaultOptions: { queries: { retry: false } },
      });
      const ui = (open: boolean) => (
        <QueryClientProvider client={qc}>
          {open && <FsBrowser open onOpenChange={() => {}} onPick={() => {}} />}
        </QueryClientProvider>
      );
      const { rerender } = render(ui(true));
      await screen.findByRole("button", { name: /^projects/ });
      expect(asked).toBe(1);
      rerender(ui(false));
      rerender(ui(true));
      await waitFor(() => expect(asked).toBe(2));
    });

    it("does not draw a row for every file in a huge folder", async () => {
      const entries = Array.from({ length: 5000 }, (_, i) => ({
        name: `game${i}.zip`,
        path: `${HOME}/game${i}.zip`,
        is_dir: false,
        hidden: false,
        size: 1,
        mtime: "2026-05-01T00:00:00Z",
      }));
      server.use(
        http.get("/api/fs/list", () =>
          HttpResponse.json({ path: HOME, parent: null, entries }),
        ),
      );
      // jsdom lays nothing out, so give the list a height to fill.
      const height = vi
        .spyOn(HTMLElement.prototype, "offsetHeight", "get")
        .mockReturnValue(300);
      renderWithClient(
        <FsBrowser
          open
          onOpenChange={() => {}}
          onPick={() => {}}
          mode="file"
        />,
      );
      const first = await screen.findByRole("button", { name: "game0.zip" });
      expect(screen.getAllByRole("listitem").length).toBeLessThan(100);
      // A screen reader still hears how long the list is.
      expect(first.closest("li")).toHaveAttribute("aria-setsize", "5000");
      expect(first.closest("li")).toHaveAttribute("aria-posinset", "1");
      height.mockRestore();
    });
  });

  describe("mame-curator-1206: the picker keeps your place", () => {
    const MAME = "/home/test/projects/mame";
    beforeEach(() => {
      server.use(
        http.get("/api/fs/list", ({ request }) => {
          const path = new URL(request.url).searchParams.get("path");
          if (path === HOME) return HttpResponse.json(homeListing);
          if (path === SUB) return HttpResponse.json(subListing);
          return HttpResponse.json({ path: MAME, parent: SUB, entries: [] });
        }),
      );
    });

    it("opening a folder puts focus on its first row, not back at the top", async () => {
      const user = userEvent.setup();
      renderWithClient(
        <FsBrowser open onOpenChange={() => {}} onPick={() => {}} large />,
      );
      await user.click(
        await screen.findByRole("button", { name: /^projects/ }),
      );
      const first = await screen.findByRole("button", { name: /^mame/ });
      await waitFor(() => expect(first).toHaveFocus());
    });

    it("opening an empty folder puts focus on Up", async () => {
      const user = userEvent.setup();
      renderWithClient(
        <FsBrowser open onOpenChange={() => {}} onPick={() => {}} large />,
      );
      await user.click(
        await screen.findByRole("button", { name: /^projects/ }),
      );
      await user.click(await screen.findByRole("button", { name: /^mame/ }));
      await screen.findByText(MAME, { selector: "code" });
      await waitFor(() =>
        expect(
          screen.getByRole("button", { name: strings.settings.fsBrowserUp }),
        ).toHaveFocus(),
      );
    });

    it("reads out the folder it is in, each time it changes", async () => {
      const user = userEvent.setup();
      renderWithClient(
        <FsBrowser open onOpenChange={() => {}} onPick={() => {}} large />,
      );
      await user.click(
        await screen.findByRole("button", { name: /^projects/ }),
      );
      await waitFor(() =>
        expect(screen.getByRole("status")).toHaveTextContent(SUB),
      );
    });

    it("stays at the top of the window, so a new folder's height cannot move it", async () => {
      renderWithClient(
        <FsBrowser open onOpenChange={() => {}} onPick={() => {}} large />,
      );
      const dialog = await screen.findByRole("dialog");
      expect(dialog).toHaveClass("top-[5dvh]", "translate-y-0");
      expect(dialog).not.toHaveClass("top-[50%]");
    });

    it("wraps a long path at its folders, and gives it the room on a narrow window", async () => {
      const LONG = "/data/games/arcade/mame/romsets/merged";
      server.use(
        http.get("/api/fs/allowed-roots", () =>
          HttpResponse.json({
            roots: [{ id: "r2", path: LONG, source: "granted" }],
          }),
        ),
      );
      renderWithClient(
        <FsBrowser open onOpenChange={() => {}} onPick={() => {}} large />,
      );
      const button = await screen.findByRole("button", { name: LONG });
      // A break after each separator, so a line ends at a folder's end.
      expect(button.querySelectorAll("wbr")).toHaveLength(6);
      // Chrome reads a break as a space; the name stays the path itself.
      expect(button).toHaveAttribute("aria-label", LONG);
      expect(button.className).not.toContain("[overflow-wrap:anywhere]");
      expect(button).toHaveClass("break-words");
      // Large text grows rem padding; a narrow window keeps it small.
      expect(screen.getByRole("dialog")).toHaveClass("p-3", "sm:p-6");
    });
  });
});
