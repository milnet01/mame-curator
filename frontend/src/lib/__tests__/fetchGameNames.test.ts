/**
 * mame-curator-1144 INV-5 — the guide copies every game its selection found,
 * across all pages.
 */
import { describe, expect, it, vi } from "vitest";
import { http, HttpResponse, server } from "@/test/handlers";
import { fetchGameNames, guideQueryFor } from "../fetchGameNames";

function pagedGames(total: number, seen: URL[] = []) {
  return http.get("/api/games", ({ request }) => {
    const url = new URL(request.url);
    seen.push(url);
    const page = Number(url.searchParams.get("page"));
    const size = Number(url.searchParams.get("page_size"));
    const start = (page - 1) * size;
    const count = Math.max(0, Math.min(size, total - start));
    const items = Array.from({ length: count }, (_, i) => ({
      short_name: `game${start + i}`,
      description: `Game ${start + i}`,
      year: 1990,
      manufacturer: "Namco",
      publisher: "Namco",
      developer: "Namco",
      badges: [],
    }));
    return HttpResponse.json({
      items,
      page,
      page_size: size,
      total,
      total_bytes: 0,
    });
  });
}

describe("fetchGameNames", () => {
  it("collects every page, so the names match total", async () => {
    const seen: URL[] = [];
    server.use(pagedGames(1200, seen));
    const onProgress = vi.fn();

    const names = await fetchGameNames({}, onProgress);

    expect(names).toHaveLength(1200);
    expect(new Set(names).size).toBe(1200);
    expect(seen.map((u) => u.searchParams.get("page"))).toEqual([
      "1",
      "2",
      "3",
    ]);
    expect(seen[0].searchParams.get("page_size")).toBe("500");
    expect(onProgress).toHaveBeenLastCalledWith(1200, 1200);
  });

  it("stops on an empty page, so a shrinking library cannot loop forever", async () => {
    server.use(
      http.get("/api/games", () =>
        HttpResponse.json({
          items: [],
          page: 1,
          page_size: 500,
          total: 10,
          total_bytes: 0,
        }),
      ),
    );
    await expect(fetchGameNames({})).resolves.toEqual([]);
  });

  it("rejects when a page fails, so no partial list reaches a copy", async () => {
    server.use(
      http.get("/api/games", () =>
        HttpResponse.json({ detail: "boom" }, { status: 500 }),
      ),
    );
    await expect(fetchGameNames({})).rejects.toBeDefined();
  });
});

describe("guideQueryFor", () => {
  it("sends no year filter for every game", () => {
    expect(guideQueryFor({ kind: "everything" })).toEqual({});
  });

  it("sends a tile's own bounds and nothing else", () => {
    expect(guideQueryFor({ kind: "tile", id: "best-of-1992" })).toEqual({
      yearFrom: 1992,
      yearTo: 1992,
    });
    expect(guideQueryFor({ kind: "tile", id: "beat-em-ups" })).toEqual({
      genre: "Platform / Fighter Scrolling",
    });
  });

  it("sends only the genre for a type of game", () => {
    expect(guideQueryFor({ kind: "genre", genre: "Maze" })).toEqual({
      genre: "Maze",
    });
  });
});
