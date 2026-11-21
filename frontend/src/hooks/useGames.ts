import {
  GamesPageSchema,
  type GamesPage,
  type ReviewStateFilter,
} from "@/api/types";
import { useInfiniteQuery } from "@tanstack/react-query";
import { apiRequest } from "@/api/client";
import { useApiQuery } from "./useApi";

export interface GamesQuery {
  page: number;
  pageSize: number;
  search?: string;
  yearFrom?: number;
  yearTo?: number;
  /** FP17: backend `letter` param. ``'#'`` selects digit-prefixed games. */
  letter?: string;
  /** FP17: backend `genre` / `publisher` / `developer` exact-match filters. */
  genre?: string;
  publisher?: string;
  developer?: string;
  onlyContested?: boolean;
  onlyOverridden?: boolean;
  onlyChdMissing?: boolean;
  onlyBiosMissing?: boolean;
  /** P14 — review-state visibility filter. Default `all` on the backend. */
  reviewState?: ReviewStateFilter;
}

export function toQueryString(q: GamesQuery): string {
  // FP16 § A: backend (api/routes/games.py:60) accepts `q`, `year_min`,
  // `year_max` — the frontend was silently sending `search`, `year_from`,
  // `year_to`, so search + year-range filtering both no-op'd in production.
  const params = new URLSearchParams();
  params.set("page", String(q.page));
  params.set("page_size", String(q.pageSize));
  if (q.search) params.set("q", q.search);
  if (q.yearFrom) params.set("year_min", String(q.yearFrom));
  if (q.yearTo) params.set("year_max", String(q.yearTo));
  if (q.letter) params.set("letter", q.letter);
  if (q.genre) params.set("genre", q.genre);
  if (q.publisher) params.set("publisher", q.publisher);
  if (q.developer) params.set("developer", q.developer);
  if (q.onlyContested) params.set("only_contested", "1");
  if (q.onlyOverridden) params.set("only_overridden", "1");
  if (q.onlyChdMissing) params.set("only_chd_missing", "1");
  if (q.onlyBiosMissing) params.set("only_bios_missing", "1");
  if (q.reviewState && q.reviewState !== "all")
    params.set("review_state", q.reviewState);
  return params.toString();
}

export function useGames(query: GamesQuery) {
  const qs = toQueryString(query);
  return useApiQuery<GamesPage>(
    ["games", qs],
    `/api/games?${qs}`,
    GamesPageSchema,
    { staleTime: 5_000 },
  );
}

/**
 * mame-curator-1234 (CR-09-5): every game the filters match, a page at a
 * time; `fetchNextPage` loads the next. Keyed under `["games"]`, so the
 * invalidations that refresh `useGames` refresh this too.
 */
export function useGamesList(query: Omit<GamesQuery, "page">) {
  const qs = toQueryString({ ...query, page: 1 });
  return useInfiniteQuery({
    queryKey: ["games", "list", qs],
    queryFn: ({ pageParam }) =>
      apiRequest<GamesPage>(
        `/api/games?${toQueryString({ ...query, page: pageParam })}`,
        GamesPageSchema,
      ),
    initialPageParam: 1,
    // An empty page ends the list too, so a total that overstates it cannot
    // keep asking for pages that are not there.
    getNextPageParam: (last, pages) => {
      const loaded = pages.reduce((n, p) => n + p.items.length, 0);
      return last.items.length > 0 && loaded < last.total
        ? pages.length + 1
        : undefined;
    },
    staleTime: 5_000,
  });
}
