/**
 * mame-curator-1146 (picture half) — choosing a game's picture one question
 * at a time, on the version guide's route. INV-11 (the Library reloads) and
 * INV-12 (what the screens offer).
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router";

import { FixVersionRoute } from "../FixVersionPage";
import type { PictureCandidates, PictureChoice } from "@/api/types";
import { strings } from "@/strings";
import { http, HttpResponse, server } from "@/test/handlers";
import { makeFakeCart, makeGameCard } from "./_libraryPageFixtures";

const fix = strings.guide.fix;
const pic = strings.guide.fix.picture;
const puck = makeGameCard({ short_name: "puck", description: "Puck World" });
const fast = makeGameCard({ short_name: "puckf", description: "Puck Fast" });

const listing = (over: Partial<PictureCandidates> = {}): PictureCandidates => ({
  short_name: "puckf",
  chosen: null,
  chosen_found: true,
  candidates: [
    { source: "esde", kind: "boxart", in_use: true },
    { source: "retroarchThumbnails", kind: "title", in_use: false },
    { source: "mystery", kind: "snap", in_use: false },
  ],
  not_asked: [],
  not_answered: [],
  ...over,
});

interface Served {
  asked: string[];
  saved: unknown[];
  cleared: number;
}

/** Serves the family and the picture routes; `fail` makes saves and clears 500. */
function serve(
  opts: {
    items?: ReturnType<typeof makeGameCard>[];
    inUse?: string | null;
    reply?: (url: URL) => PictureCandidates;
    fail?: () => boolean;
  } = {},
): Served {
  const served: Served = { asked: [], saved: [], cleared: 0 };
  const failure = () =>
    HttpResponse.json(
      { code: "internal", detail: "disk full", fields: [] },
      { status: 500 },
    );
  server.use(
    http.get("/api/games/:name/alternatives", () =>
      HttpResponse.json({
        parent: "puck",
        items: opts.items ?? [fast],
        in_use: opts.inUse === undefined ? "puckf" : opts.inUse,
      }),
    ),
    http.get("/api/games/:name/picture/candidates", ({ request }) => {
      const url = new URL(request.url);
      served.asked.push(url.pathname + url.search);
      return HttpResponse.json((opts.reply ?? (() => listing()))(url));
    }),
    http.put("/api/games/:name/picture", async ({ request, params }) => {
      if (opts.fail?.()) return failure();
      const body = (await request.json()) as PictureChoice;
      served.saved.push(body);
      return HttpResponse.json({ short_name: params.name, chosen: body });
    }),
    http.delete("/api/games/:name/picture", ({ params }) => {
      if (opts.fail?.()) return failure();
      served.cleared += 1;
      return HttpResponse.json({ short_name: params.name, chosen: null });
    }),
  );
  return served;
}

function renderFix(address = "/fix/puckf") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const invalidate = vi.spyOn(client, "invalidateQueries");
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[address]}>
        <Routes>
          <Route
            path="/fix/:shortName"
            element={<FixVersionRoute cart={makeFakeCart()} />}
          />
          <Route path="/" element={<p>the library</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return { invalidate };
}

const pictureButton = (label: RegExp) =>
  screen.findByRole("button", { name: label });

describe("the picture guide", () => {
  it("opens at the picture question for a game with one version", async () => {
    serve();
    renderFix();
    expect(
      await screen.findByRole("heading", { name: pic.heading }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: pic.whatHeading })).toBeNull();
    expect(screen.getByText(pic.thisVersionOnly)).toBeInTheDocument();
  });

  it("asks what to fix first when the game has several versions", async () => {
    serve({ items: [puck, fast] });
    const user = userEvent.setup();
    renderFix();
    await screen.findByRole("heading", { name: pic.whatHeading });
    await user.click(screen.getByRole("button", { name: pic.whatVersion }));
    expect(
      await screen.findByRole("heading", { name: fix.heading }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: strings.guide.back }));
    await user.click(
      await screen.findByRole("button", { name: pic.whatPicture }),
    );
    expect(
      await screen.findByRole("heading", { name: pic.heading }),
    ).toBeInTheDocument();
  });

  it("says it is looking while the list loads", async () => {
    serve();
    server.use(
      http.get(
        "/api/games/:name/picture/candidates",
        () => new Promise(() => {}),
      ),
    );
    renderFix();
    expect(await screen.findByRole("status")).toHaveTextContent(pic.looking);
  });

  it("shows each picture large, with its label and place, and marks the one in use", async () => {
    serve();
    renderFix();
    const inUse = await pictureButton(/Box or flyer, from your ES-DE pictures/);
    expect(inUse).toHaveTextContent(fix.inUse);
    const title = await pictureButton(
      /Title screen, from your RetroArch pictures/,
    );
    expect(title).not.toHaveTextContent(fix.inUse);
    expect(title.querySelector("img")).toHaveAttribute(
      "src",
      "/media/puckf/title?source=retroarchThumbnails",
    );
    expect(title.querySelector("img")).toHaveAttribute("alt", "");
    // A source the table does not name shows its own name.
    expect(
      await pictureButton(/In-game screen, from mystery/),
    ).toBeInTheDocument();
  });

  it("acts on the version in use, not the one in the address", async () => {
    const served = serve({ inUse: "puck", items: [puck] });
    renderFix();
    await pictureButton(/Box or flyer/);
    expect(served.asked[0]).toMatch(/^\/api\/games\/puck\/picture\/candidates/);
  });

  it("offers the usual picture only when a choice is stored", async () => {
    serve();
    renderFix();
    await pictureButton(/Box or flyer/);
    expect(screen.queryByRole("button", { name: pic.useUsual })).toBeNull();
  });

  it("offers more places only when some were not asked or did not answer", async () => {
    serve();
    renderFix();
    await pictureButton(/Box or flyer/);
    expect(screen.queryByRole("button", { name: pic.lookFurther })).toBeNull();
    expect(screen.queryByText(pic.notAnswered)).toBeNull();
  });

  it("looks in more places when asked, and says when some did not answer", async () => {
    const served = serve({
      reply: (url) =>
        url.searchParams.get("further") === "true"
          ? listing({ not_answered: ["mobyGames"] })
          : listing({ not_asked: ["arcadeDB"] }),
    });
    const user = userEvent.setup();
    renderFix();
    await user.click(
      await screen.findByRole("button", { name: pic.lookFurther }),
    );
    expect(await screen.findByText(pic.notAnswered)).toBeInTheDocument();
    expect(served.asked.at(-1)).toContain("further=true");
    expect(
      screen.getByRole("button", { name: pic.lookFurther }),
    ).toBeInTheDocument();
  });

  it("says when the chosen picture cannot be found now", async () => {
    serve({
      reply: () =>
        listing({
          chosen: { source: "arcadeDB", kind: "title" },
          chosen_found: false,
        }),
    });
    renderFix();
    expect(await screen.findByText(pic.chosenMissing)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: pic.useUsual }),
    ).toBeInTheDocument();
  });

  it("sends nothing when the picture in use is chosen", async () => {
    const served = serve();
    const user = userEvent.setup();
    renderFix();
    await user.click(await pictureButton(/Box or flyer/));
    expect(
      await screen.findByRole("heading", { name: pic.alreadyUsing }),
    ).toBeInTheDocument();
    expect(served.saved).toEqual([]);
  });

  it("saves a choice, shows it, and reloads the Library and the versions", async () => {
    const served = serve();
    const user = userEvent.setup();
    const { invalidate } = renderFix();
    await user.click(await pictureButton(/Title screen/));
    await screen.findByRole("heading", { name: pic.savedHeading });
    expect(served.saved).toEqual([
      { source: "retroarchThumbnails", kind: "title" },
    ]);
    const step = screen.getByTestId("guide-step");
    expect(step.querySelector("img")).toHaveAttribute(
      "src",
      "/media/puckf/boxart?v=retroarchThumbnails.title",
    );
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["games"] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["alternatives"] });
    await user.click(screen.getByRole("link", { name: fix.toLibrary }));
    expect(await screen.findByText("the library")).toBeInTheDocument();
  });

  it("goes back to the usual picture", async () => {
    const served = serve({
      reply: () => listing({ chosen: { source: "esde", kind: "boxart" } }),
    });
    const user = userEvent.setup();
    const { invalidate } = renderFix();
    await user.click(await screen.findByRole("button", { name: pic.useUsual }));
    expect(
      await screen.findByRole("heading", { name: pic.clearedHeading }),
    ).toBeInTheDocument();
    expect(served.cleared).toBe(1);
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["games"] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["alternatives"] });
  });

  it("says a failed save plainly, changes nothing, and can try again", async () => {
    let fail = true;
    const served = serve({ fail: () => fail });
    const user = userEvent.setup();
    renderFix();
    await user.click(await pictureButton(/Title screen/));
    await screen.findByRole("heading", { name: fix.failedHeading });
    expect(screen.getByRole("alert")).toHaveTextContent(/.+/);
    expect(screen.getByText(fix.nothingChanged)).toBeInTheDocument();
    fail = false;
    await user.click(screen.getByRole("button", { name: fix.tryAgain }));
    await screen.findByRole("heading", { name: pic.savedHeading });
    expect(served.saved).toHaveLength(1);
  });

  it("says a failed clear plainly and goes back to the choice", async () => {
    serve({
      reply: () => listing({ chosen: { source: "esde", kind: "boxart" } }),
      fail: () => true,
    });
    const user = userEvent.setup();
    renderFix();
    await user.click(await screen.findByRole("button", { name: pic.useUsual }));
    await screen.findByRole("heading", { name: fix.failedHeading });
    expect(screen.getByRole("alert")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: strings.guide.back }));
    expect(
      await screen.findByRole("heading", { name: pic.heading }),
    ).toBeInTheDocument();
  });

  it("says when no picture was found, and still offers more places", async () => {
    serve({
      reply: () => listing({ candidates: [], not_asked: ["arcadeDB"] }),
    });
    renderFix();
    expect(await screen.findByText(pic.none)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: pic.lookFurther }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: fix.toLibrary }),
    ).toBeInTheDocument();
  });
});
