/**
 * mame-curator-1144 — what the Library does when a copy ends, against P15 D9:
 * clear on success, retain on partial or failed.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { toast } from "sonner";

import { LIBRARY_VIEW_KEY } from "@/lib/libraryView";
import { strings } from "@/strings";
import { http, HttpResponse, server } from "@/test/handlers";
import { LibraryPage } from "../LibraryPage";
import {
  libraryPageBaseHandlers,
  makeFakeCart,
  makeGamesPage,
  renderLibraryPageTree,
  setupCheckFixture,
} from "./_libraryPageFixtures";
import { config as appConfig } from "./_settingsPageFixtures";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
}));

class MockEventSource {
  static instances: MockEventSource[] = [];
  static CLOSED = 2;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  onopen: ((ev: Event) => void) | null = null;
  readyState = 1;
  constructor() {
    MockEventSource.instances.push(this);
  }
  emit(event: string, payload: Record<string, unknown> = {}) {
    this.onmessage?.(
      new MessageEvent("message", {
        data: JSON.stringify({ event, payload, ts: new Date().toISOString() }),
      }),
    );
  }
  close() {
    this.readyState = MockEventSource.CLOSED;
  }
}

type Policy = "always" | "on_success" | "never";

function serve(policy: Policy | "config-pending") {
  server.use(
    http.get("/api/config", () =>
      policy === "config-pending"
        ? new Promise<never>(() => {})
        : HttpResponse.json({
            ...appConfig,
            ui: { ...appConfig.ui, cart_clear_on_copy: policy },
          }),
    ),
    http.get("/api/games", () => HttpResponse.json(makeGamesPage([]))),
    http.post("/api/games/validate", () =>
      HttpResponse.json({ existing: ["pacman"], missing: [] }),
    ),
    http.post("/api/copy/start", () => HttpResponse.json({ job_id: "job-1" })),
    ...libraryPageBaseHandlers(),
  );
}

function renderPage() {
  const clear = vi.fn();
  const cart = {
    ...makeFakeCart(),
    items: [{ shortName: "pacman" }],
    clear,
  };
  renderLibraryPageTree(
    <LibraryPage
      cart={cart}
      cartExpanded={false}
      onCartExpandedChange={() => {}}
    />,
  );
  return { clear };
}

const copyButton = () =>
  screen.findByRole("button", { name: strings.library.actions.copy });

async function startCopy(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await copyButton());
  await screen.findByRole("dialog");
  return MockEventSource.instances[0];
}

/** Gives the config time to load before a copy ends. */
async function configLoaded() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 30));
  });
}

beforeEach(() => {
  MockEventSource.instances = [];
  vi.stubGlobal("EventSource", MockEventSource);
  localStorage.setItem(LIBRARY_VIEW_KEY, "full");
  vi.mocked(toast.success).mockClear();
  vi.mocked(toast.error).mockClear();
  vi.mocked(toast.warning).mockClear();
});

describe("LibraryPage when a copy ends", () => {
  it("on_success, OK: clears the cart, closes the modal, says it worked", async () => {
    serve("on_success");
    const user = userEvent.setup();
    const { clear } = renderPage();
    await configLoaded();
    const es = await startCopy(user);
    act(() => es.emit("job_finished", { status: "OK" }));
    await waitFor(() => expect(clear).toHaveBeenCalledOnce());
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(toast.success).toHaveBeenCalledWith(
      strings.guide.copying.finishedHeading,
    );
  });

  it("on_success, partial failure: keeps the cart and stays open with the alert (P15 D9)", async () => {
    serve("on_success");
    const user = userEvent.setup();
    const { clear } = renderPage();
    await configLoaded();
    const es = await startCopy(user);
    act(() => es.emit("job_finished", { status: "PARTIAL_FAILURE" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      strings.guide.copying.partial,
    );
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(clear).not.toHaveBeenCalled();
    expect(toast.success).not.toHaveBeenCalled();
  });

  it("on_success, crash: keeps the cart and stays open with the alert", async () => {
    serve("on_success");
    const user = userEvent.setup();
    const { clear } = renderPage();
    await configLoaded();
    const es = await startCopy(user);
    act(() => es.emit("job_aborted", { reason: "boom" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      strings.copy.failed,
    );
    expect(clear).not.toHaveBeenCalled();
  });

  it("never, OK: keeps the cart and stays open saying it worked", async () => {
    serve("never");
    const user = userEvent.setup();
    const { clear } = renderPage();
    await configLoaded();
    const es = await startCopy(user);
    act(() => es.emit("job_finished", { status: "OK" }));
    expect(await screen.findByRole("status")).toHaveTextContent(
      strings.guide.copying.finishedHeading,
    );
    expect(clear).not.toHaveBeenCalled();
  });

  it("always, partial failure: clears as asked, but stays open with the alert", async () => {
    serve("always");
    const user = userEvent.setup();
    const { clear } = renderPage();
    await configLoaded();
    const es = await startCopy(user);
    act(() => es.emit("job_finished", { status: "PARTIAL_FAILURE" }));
    await waitFor(() => expect(clear).toHaveBeenCalledOnce());
    expect(screen.getByRole("alert")).toHaveTextContent(
      strings.guide.copying.partial,
    );
  });

  it("always, the user's own Cancel: clears and closes", async () => {
    serve("always");
    const user = userEvent.setup();
    const { clear } = renderPage();
    await configLoaded();
    const es = await startCopy(user);
    act(() => es.emit("job_aborted", { reason: "CANCELLED" }));
    await waitFor(() => expect(clear).toHaveBeenCalledOnce());
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("always, crash: clears as asked, but stays open with the alert", async () => {
    serve("always");
    const user = userEvent.setup();
    const { clear } = renderPage();
    await configLoaded();
    const es = await startCopy(user);
    act(() => es.emit("job_aborted", { reason: "boom" }));
    await waitFor(() => expect(clear).toHaveBeenCalledOnce());
    expect(screen.getByRole("alert")).toHaveTextContent(strings.copy.failed);
  });

  it("always, lost stream: the outcome is unknown, so the cart stays", async () => {
    serve("always");
    const user = userEvent.setup();
    const { clear } = renderPage();
    await configLoaded();
    const es = await startCopy(user);
    act(() => {
      es.readyState = MockEventSource.CLOSED;
      es.onerror?.(new Event("error"));
    });
    expect(await screen.findByRole("alert")).toHaveTextContent(
      strings.copy.lost,
    );
    expect(clear).not.toHaveBeenCalled();
  });

  it("config not loaded yet: a finish clears nothing, for it may be a never user's", async () => {
    serve("config-pending");
    const user = userEvent.setup();
    const { clear } = renderPage();
    const es = await startCopy(user);
    act(() => es.emit("job_finished", { status: "OK" }));
    await configLoaded();
    expect(clear).not.toHaveBeenCalled();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(toast.success).not.toHaveBeenCalled();
  });
});

describe("LibraryPage during a copy", () => {
  it("Esc does not lose control of a running copy", async () => {
    serve("on_success");
    const user = userEvent.setup();
    renderPage();
    await configLoaded();
    await startCopy(user);
    await user.keyboard("{Escape}");
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: strings.copy.pause }),
    ).toBeInTheDocument();
  });

  it("Copy stays off from validate success until start has answered", async () => {
    let answerStart = () => {};
    serve("on_success");
    server.use(
      http.post(
        "/api/copy/start",
        () =>
          new Promise((resolve) => {
            answerStart = () => resolve(HttpResponse.json({ job_id: "job-1" }));
          }),
      ),
    );
    const user = userEvent.setup();
    renderPage();
    await configLoaded();
    await user.click(await copyButton());
    await configLoaded();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(await copyButton()).toBeDisabled();
    answerStart();
    await screen.findByRole("dialog");
  });
});

describe("LibraryPage when a copy is refused", () => {
  function renderCart(items: { shortName: string; chosenVariant?: string }[]) {
    const remove = vi.fn();
    renderLibraryPageTree(
      <LibraryPage
        cart={{ ...makeFakeCart(), items, remove }}
        cartExpanded={false}
        onCartExpandedChange={() => {}}
      />,
    );
    return { remove };
  }

  it("says so when the server refuses the start", async () => {
    serve("on_success");
    server.use(
      http.post("/api/copy/start", () =>
        HttpResponse.json(
          {
            code: "copy_names_unknown",
            detail: "raw",
            fields: [
              { loc: "selected_names", msg: "gone", type: "unknown_game" },
            ],
          },
          { status: 422 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderCart([{ shortName: "pacman" }]);
    await user.click(await copyButton());

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(
        `${strings.errors.byCode.copy_names_unknown} gone`,
      ),
    );
  });

  it("checks the variant it would send, and drops one the library lost", async () => {
    const sent: string[][] = [];
    const checked: string[][] = [];
    serve("on_success");
    server.use(
      http.post("/api/games/validate", async ({ request }) => {
        const { short_names } = (await request.json()) as {
          short_names: string[];
        };
        checked.push(short_names);
        return HttpResponse.json({
          existing: short_names.filter((n) => n !== "gonevariant"),
          missing: short_names.filter((n) => n === "gonevariant"),
        });
      }),
      http.post("/api/copy/start", async ({ request }) => {
        const body = (await request.json()) as { selected_names: string[] };
        sent.push(body.selected_names);
        return HttpResponse.json({ job_id: "job-1" });
      }),
    );
    const user = userEvent.setup();
    const { remove } = renderCart([
      { shortName: "pacman", chosenVariant: "pacmanf" },
      { shortName: "dkong", chosenVariant: "gonevariant" },
    ]);
    await user.click(await copyButton());

    await screen.findByRole("dialog");
    expect(checked).toEqual([["pacmanf", "gonevariant"]]);
    expect(sent).toEqual([["pacmanf"]]);
    expect(remove).toHaveBeenCalledExactlyOnceWith("dkong");
    expect(toast.warning).toHaveBeenCalledWith(
      strings.library.cart.validateDroppedToast(1),
    );
  });

  // mame-curator-1183: with no game list loaded, every name comes back missing.
  describe("when the game list is not loaded", () => {
    function everyNameMissing() {
      const started = vi.fn();
      serve("on_success");
      server.use(
        http.post("/api/games/validate", async ({ request }) => {
          const { short_names } = (await request.json()) as {
            short_names: string[];
          };
          return HttpResponse.json({ existing: [], missing: short_names });
        }),
        http.post("/api/copy/start", () => {
          started();
          return HttpResponse.json({ job_id: "job-1" });
        }),
      );
      return { started };
    }
    const inSetupMode = () =>
      HttpResponse.json({ ...setupCheckFixture, setup_required: true });

    it("keeps the cart and says why", async () => {
      const { started } = everyNameMissing();
      server.use(http.get("/api/setup/check", inSetupMode));
      const user = userEvent.setup();
      const { remove } = renderCart([
        { shortName: "pacman" },
        { shortName: "dkong" },
      ]);
      await user.click(await copyButton());

      await waitFor(() =>
        expect(toast.error).toHaveBeenCalledWith(
          strings.errors.byCode.copy_setup_required,
        ),
      );
      expect(remove).not.toHaveBeenCalled();
      expect(toast.warning).not.toHaveBeenCalled();
      expect(started).not.toHaveBeenCalled();
    });

    it("asks afresh, for the app may have restarted since the page loaded", async () => {
      everyNameMissing();
      const user = userEvent.setup();
      const { remove } = renderCart([{ shortName: "pacman" }]);
      await configLoaded();
      server.use(http.get("/api/setup/check", inSetupMode));
      await user.click(await copyButton());

      await waitFor(() =>
        expect(toast.error).toHaveBeenCalledWith(
          strings.errors.byCode.copy_setup_required,
        ),
      );
      expect(remove).not.toHaveBeenCalled();
    });

    it("keeps the cart when it cannot tell", async () => {
      everyNameMissing();
      const user = userEvent.setup();
      const { remove } = renderCart([{ shortName: "pacman" }]);
      await configLoaded();
      server.use(
        http.get("/api/setup/check", () =>
          HttpResponse.json(
            { code: "boom", detail: "setup check broke", fields: [] },
            { status: 500 },
          ),
        ),
      );
      await user.click(await copyButton());

      await waitFor(() => expect(toast.error).toHaveBeenCalled());
      expect(remove).not.toHaveBeenCalled();
      expect(toast.warning).not.toHaveBeenCalled();
    });
  });
});
