/**
 * mame-curator-1146 (version half) — choosing a version one question at a
 * time. Saving goes through mame-curator-1149's path, which
 * LibraryPage_version_choice.test.tsx covers from the Library.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router";
import { toast } from "sonner";

import { FixVersionRoute } from "../FixVersionPage";
import type { UseCartResult } from "@/hooks/useCart";
import { strings } from "@/strings";
import { http, HttpResponse, server } from "@/test/handlers";
import { makeFakeCart, makeGameCard } from "./_libraryPageFixtures";

vi.mock("sonner", async (original) => ({
  ...(await original<typeof import("sonner")>()),
  toast: { success: vi.fn(), warning: vi.fn(), error: vi.fn() },
}));

const fix = strings.guide.fix;
const parent = makeGameCard({ short_name: "puck", description: "Puck World" });
const fast = makeGameCard({ short_name: "puckf", description: "Puck Fast" });
const junior = {
  ...makeGameCard({ short_name: "puckj", description: "Puck Junior" }),
  year: 1982,
  manufacturer: "Namco (Midway license)",
};

/** Serves the Puck family; a POST answers as `reply` says. */
function serve(
  reply: () => Response,
  items = [parent, fast, junior],
  inUse: string | null = "puckf",
) {
  const posted: unknown[] = [];
  server.use(
    http.get("/api/games/:name/alternatives", () =>
      HttpResponse.json({ parent: "puck", items, in_use: inUse }),
    ),
    http.post("/api/overrides", async ({ request }) => {
      posted.push(await request.json());
      return reply();
    }),
  );
  return posted;
}

const accepted = (warnings: string[] = [], unusable: string[] = []) =>
  HttpResponse.json({ entries: { puck: "puckj" }, warnings, unusable });
const refused = () =>
  HttpResponse.json(
    { code: "override_rejected", detail: "no", fields: [] },
    { status: 422 },
  );

/** Renders the guide; `toVersions` answers its first question for the
 *  version half (mame-curator-1146, picture half). */
async function renderFix(
  cart: UseCartResult = makeFakeCart(),
  toVersions = true,
) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/fix/puckf"]}>
        <Routes>
          <Route
            path="/fix/:shortName"
            element={<FixVersionRoute cart={cart} />}
          />
          <Route path="/" element={<p>the library</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  if (toVersions) {
    await userEvent.click(
      await screen.findByRole("button", { name: fix.picture.whatVersion }),
    );
  }
}

const versionButton = (name: string) =>
  screen.findByRole("button", { name: new RegExp(name) });

beforeEach(() => vi.clearAllMocks());

describe("the version guide", () => {
  it("offers every version with its year and maker, and marks the one in use", async () => {
    serve(accepted);
    await renderFix();
    await screen.findByRole("heading", { name: fix.heading });
    const juniorButton = await versionButton("Puck Junior");
    expect(juniorButton).toHaveTextContent("1982");
    expect(juniorButton).toHaveTextContent("Namco (Midway license)");
    expect(juniorButton).not.toHaveTextContent(fix.inUse);
    expect(await versionButton("Puck World")).not.toHaveTextContent(fix.inUse);
    expect(await versionButton("Puck Fast")).toHaveTextContent(fix.inUse);
  });

  it("marks the version the server says is in use, not the one in the address", async () => {
    // mame-curator-1197: a hand-typed /fix/puckf while Puck World is in use.
    const posted = serve(accepted, [parent, fast, junior], "puck");
    const user = userEvent.setup();
    await renderFix();

    expect(await versionButton("Puck World")).toHaveTextContent(fix.inUse);
    expect(await versionButton("Puck Fast")).not.toHaveTextContent(fix.inUse);
    await user.click(await versionButton("Puck Fast"));
    expect(
      await screen.findByRole("heading", {
        name: strings.library.overrideApplied("Puck Fast"),
      }),
    ).toBeInTheDocument();
    expect(posted).toEqual([{ parent: "puck", winner: "puckf" }]);
  });

  it("saves a choice under the family's parent and says what is in use now", async () => {
    const posted = serve(accepted);
    const setVariant = vi.fn();
    await renderFix({
      ...makeFakeCart(),
      items: [{ shortName: "puckf" }],
      setVariant,
    });
    await userEvent.click(await versionButton("Puck Junior"));
    await screen.findByRole("heading", {
      name: strings.library.overrideApplied("Puck Junior"),
    });
    expect(posted).toEqual([{ parent: "puck", winner: "puckj" }]);
    expect(setVariant).toHaveBeenCalledWith("puckf", "puckj");
    // The screen says it, so no message pops up as well.
    expect(toast.success).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("link", { name: fix.toLibrary }));
    expect(await screen.findByText("the library")).toBeInTheDocument();
  });

  it("says when the choice took but older choices could not be used", async () => {
    serve(() =>
      accepted(["override key 'ghost' is not a known parent"], ["ghost"]),
    );
    await renderFix();
    await userEvent.click(await versionButton("Puck Junior"));
    expect(
      await screen.findByText(strings.library.overrideOldChoicesUnusable(1)),
    ).toBeInTheDocument();
  });

  it("forgets an older choice that cannot be used, when asked", async () => {
    serve(() =>
      accepted(["override key 'ghost' is not a known parent"], ["ghost"]),
    );
    const forgotten: string[] = [];
    server.use(
      http.delete("/api/overrides/:parent", ({ params }) => {
        forgotten.push(String(params.parent));
        return HttpResponse.json({
          entries: { puck: "puckj" },
          warnings: [],
          unusable: [],
        });
      }),
    );
    await renderFix();
    await userEvent.click(await versionButton("Puck Junior"));
    await userEvent.click(
      await screen.findByRole("button", {
        name: strings.library.overrideForgetOld(1),
      }),
    );
    expect(
      await screen.findByText(strings.library.overrideForgotten(1)),
    ).toBeInTheDocument();
    expect(forgotten).toEqual(["ghost"]);
    expect(
      screen.queryByText(strings.library.overrideOldChoicesUnusable(1)),
    ).not.toBeInTheDocument();
  });

  it("says so when an older choice cannot be forgotten", async () => {
    serve(() =>
      accepted(["override key 'ghost' is not a known parent"], ["ghost"]),
    );
    server.use(
      http.delete("/api/overrides/:parent", () =>
        HttpResponse.json(
          { code: "override_not_found", detail: "no", fields: [] },
          { status: 404 },
        ),
      ),
    );
    await renderFix();
    await userEvent.click(await versionButton("Puck Junior"));
    await userEvent.click(
      await screen.findByRole("button", {
        name: strings.library.overrideForgetOld(1),
      }),
    );
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(
      screen.getByText(strings.library.overrideOldChoicesUnusable(1)),
    ).toBeInTheDocument();
  });

  it("changes nothing when the version in use is chosen", async () => {
    const posted = serve(accepted);
    await renderFix();
    await userEvent.click(await versionButton("Puck Fast"));
    await screen.findByRole("heading", { name: fix.unchanged("Puck Fast") });
    expect(posted).toEqual([]);
  });

  it("says what went wrong when the save fails, and can try again", async () => {
    let fail = true;
    const posted = serve(() => (fail ? refused() : accepted()));
    await renderFix();
    await userEvent.click(await versionButton("Puck Junior"));
    await screen.findByRole("heading", { name: fix.failedHeading });
    expect(screen.getByRole("alert")).toHaveTextContent(
      strings.errors.byCode.override_rejected,
    );
    expect(screen.getByText(fix.nothingChanged)).toBeInTheDocument();
    // mame-curator-1195: the screen says it; no pop-up repeats it.
    expect(toast.error).not.toHaveBeenCalled();
    fail = false;
    await userEvent.click(screen.getByRole("button", { name: fix.tryAgain }));
    await screen.findByRole("heading", {
      name: strings.library.overrideApplied("Puck Junior"),
    });
    expect(posted).toHaveLength(2);
  });

  it("goes back from a failed save to the choice", async () => {
    serve(refused);
    await renderFix();
    await userEvent.click(await versionButton("Puck Junior"));
    await screen.findByRole("heading", { name: fix.failedHeading });
    await userEvent.click(
      screen.getByRole("button", { name: strings.guide.back }),
    );
    expect(
      await screen.findByRole("heading", { name: fix.heading }),
    ).toBeInTheDocument();
  });

  it("says so when the versions cannot be loaded, and can try again", async () => {
    let fail = true;
    server.use(
      http.get("/api/games/:name/alternatives", () =>
        fail
          ? HttpResponse.json(
              { code: "internal", detail: "boom", fields: [] },
              { status: 500 },
            )
          : HttpResponse.json({
              parent: "puck",
              items: [parent, fast],
              in_use: "puckf",
            }),
      ),
    );
    await renderFix(makeFakeCart(), false);
    await screen.findByRole("heading", { name: strings.guide.loadFailed });
    expect(
      screen.getByRole("link", { name: fix.toLibrary }),
    ).toBeInTheDocument();
    fail = false;
    await userEvent.click(screen.getByRole("button", { name: fix.tryAgain }));
    expect(
      await screen.findByRole("heading", { name: fix.picture.whatHeading }),
    ).toBeInTheDocument();
  });

  it("offers the way back to the Library on the choosing screen", async () => {
    serve(accepted);
    await renderFix();
    await screen.findByRole("heading", { name: fix.heading });
    await userEvent.click(screen.getByRole("link", { name: fix.toLibrary }));
    expect(await screen.findByText("the library")).toBeInTheDocument();
  });
});
