/**
 * The Library's games for the current filters, a page at a time, and the
 * featured tiles' counts (mame-curator-1234, CR-09-12: out of
 * `useLibraryController.ts`, over its size cap).
 */
import { useCallback, useMemo } from "react";
import { useQueries } from "@tanstack/react-query";
import { type FilterSidebarState } from "@/components/library/FiltersSidebar";
import { useGamesList, type GamesQuery } from "@/hooks/useGames";
import { strings } from "@/strings";
import type { GameCard, GamesPage } from "@/api/types";
import { DEFAULT_FILTERS, fetchTileCount } from "./libraryPageHelpers";

export function useLibraryGames(filters: FilterSidebarState) {
  // mame-curator-1150: year bounds leave out games with no year, so the
  // untouched default range sends none.
  const yearsChosen =
    filters.yearRange[0] !== DEFAULT_FILTERS.yearRange[0] ||
    filters.yearRange[1] !== DEFAULT_FILTERS.yearRange[1];
  const query: Omit<GamesQuery, "page"> = {
    pageSize: 200,
    search: filters.search,
    yearFrom: yearsChosen ? filters.yearRange[0] : undefined,
    yearTo: yearsChosen ? filters.yearRange[1] : undefined,
    letter: filters.letter ?? undefined,
    genre: filters.genre ?? undefined,
    publisher: filters.publisher ?? undefined,
    developer: filters.developer ?? undefined,
    onlyContested: filters.onlyContested,
    onlyOverridden: filters.onlyOverridden,
    onlyChdMissing: filters.onlyChdMissing,
    onlyBiosMissing: filters.onlyBiosMissing,
    reviewState: filters.reviewState,
  };
  // mame-curator-1234 (CR-09-5): every game, a page at a time as the user
  // scrolls. FP24-V: `cards` keeps its reference until a page lands, so the
  // useMemo/useEffect deps downstream don't re-run on every render.
  const games = useGamesList(query);
  const cards: GameCard[] = useMemo(
    () => games.data?.pages.flatMap((p) => p.items) ?? [],
    [games.data],
  );
  const total = games.data?.pages[0]?.total ?? 0;
  const { hasNextPage, isFetchingNextPage, fetchNextPage } = games;
  const loadMore = useCallback(() => {
    if (hasNextPage && !isFetchingNextPage) void fetchNextPage();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  // Fan out one count query per featured tile. useQueries keeps hook count
  // fixed (Rules of Hooks); tiles array is `as const` so length is stable.
  const tileQueries = useQueries({
    queries: strings.library.featured.tiles.map((tile) => ({
      queryKey: ["games", "tile-count", tile.id],
      queryFn: () => fetchTileCount(tile),
      staleTime: 5 * 60 * 1000,
    })),
  });
  // FP24-Z: omit `?? 0` so still-loading tiles surface as `undefined`
  // and FeaturedTilesRow's `count !== undefined` guard suppresses the
  // count label until the query lands. Otherwise tiles flash a
  // misleading "0 games" before the real number paints.
  const tileCounts: Record<string, number | undefined> = Object.fromEntries(
    strings.library.featured.tiles.map((tile, idx) => [
      tile.id,
      (tileQueries[idx].data as GamesPage | undefined)?.total,
    ]),
  );

  return {
    query,
    games,
    cards,
    total,
    hasMore: hasNextPage,
    loadMore,
    tileCounts,
  };
}
