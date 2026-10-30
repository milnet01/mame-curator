/**
 * mame-curator-1144 — what the guide selected, and every game name it found.
 * The guide does not use the cart, so it has no MAX_CART_SIZE and cannot
 * change a cart the user has half built.
 */
import { ApiError, apiRequest, STATUS_UNSENT } from "@/api/client";
import { GamesPageSchema, type GamesPage } from "@/api/types";
import { toQueryString, type GamesQuery } from "@/hooks/useGames";
import { strings } from "@/strings";

export type GuideQuery = Omit<GamesQuery, "page" | "pageSize">;

export type GuideSelection =
  | { kind: "everything" }
  | { kind: "tile"; id: string }
  | { kind: "genre"; genre: string };

const PAGE_SIZE = 500; // The API's page_size maximum.

/** Only the selection's own filters. The Library's default year range would
 *  hide undated games, so it never applies here. */
export function guideQueryFor(selection: GuideSelection): GuideQuery {
  if (selection.kind === "genre") return { genre: selection.genre };
  if (selection.kind === "tile") {
    const tile = strings.library.featured.tiles.find(
      (t) => t.id === selection.id,
    );
    return tile ? { ...tile.query } : {};
  }
  return {};
}

/** A rebuild mid-paging shifts the pages, so the list cannot be trusted. */
function listChanged(): ApiError {
  return new ApiError(
    {
      code: "game_list_changed",
      detail: strings.guide.finds.listChanged,
      fields: [],
    },
    STATUS_UNSENT,
  );
}

export async function fetchGameNames(
  query: GuideQuery,
  onProgress?: (done: number, total: number) => void,
  signal?: AbortSignal,
): Promise<string[]> {
  const names = new Set<string>();
  let total: number | undefined;
  for (let page = 1; ; page += 1) {
    const qs = toQueryString({ ...query, page, pageSize: PAGE_SIZE });
    const data = await apiRequest<GamesPage>(
      `/api/games?${qs}`,
      GamesPageSchema,
      { signal },
    );
    if (total !== undefined && data.total !== total) throw listChanged();
    total = data.total;
    for (const card of data.items) names.add(card.short_name);
    onProgress?.(names.size, total);
    signal?.throwIfAborted();
    if (names.size >= total) return [...names];
    if (data.items.length === 0) throw listChanged();
  }
}
