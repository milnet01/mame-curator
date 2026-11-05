/**
 * `LibraryPage` controller hook (mame-curator-1077 — split the page
 * under the §2 frontend file-size hard cap of 350 lines). Holds all of
 * the page's non-render logic — state, data hooks, derived values,
 * handlers, and effects — so `LibraryPage.tsx` stays a thin view. The
 * page's JSX is deliberately left in place so the source-text
 * structural tests (`LibraryPage_error_boundary`, `landmark_labels`)
 * keep asserting against the rendered tree's shape.
 */
import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router";
import { toast } from "sonner";
import { useQueries } from "@tanstack/react-query";
import { type FilterSidebarState } from "@/components/library/FiltersSidebar";
import { useAlternatives, useLaunchGame } from "@/hooks/useAlternatives";
import {
  type CartItem,
  MAX_CART_SIZE,
  type UseCartResult,
} from "@/hooks/useCart";
import { useCopySession } from "@/hooks/useCopySession";
import { useDryRun } from "@/hooks/useDryRun";
import { useFacets } from "@/hooks/useFacets";
import { toQueryString, useGames, type GamesQuery } from "@/hooks/useGames";
import {
  useReviewState,
  useReviewStateClear,
  useReviewStateSet,
} from "@/hooks/useReviewState";
import { useValidateCart } from "@/hooks/useValidateCart";
import { useConfig, useConfigPatch } from "@/hooks/useConfig";
import { useSessions, useSessionUpsert } from "@/hooks/useSessions";
import { useSetupCheck } from "@/hooks/useSetupCheck";
import { toastApiError } from "@/lib/apiErrorToast";
import { copyOutcome } from "@/lib/copyOutcome";
import { strings } from "@/strings";
import { apiRequest } from "@/api/client";
import { GamesPageSchema, type GamesPage } from "@/api/types";
import type {
  DryRunReport,
  GameCard,
  LayoutName,
  Session,
  ThemeName,
} from "@/api/types";
import {
  DEFAULT_FILTERS,
  fetchTileCount,
  filtersForGuideSelection,
  filtersForTile,
  readGuideSelection,
  readReturnFocus,
  readWalkthroughPref,
} from "./libraryPageHelpers";
import { useVersionChoice } from "./useVersionChoice";

export function useLibraryController(cart: UseCartResult) {
  // mame-curator-1144: a selection from the guide's "Look through them first"
  // applies once, as the first state of a freshly mounted page.
  const location = useLocation();
  const navigate = useNavigate();
  const [guideSelection] = useState(() => readGuideSelection(location.state));
  const [returnFocus] = useState(() => readReturnFocus(location.state));
  const [filters, setFilters] = useState<FilterSidebarState>(() =>
    filtersForGuideSelection(guideSelection),
  );
  const [openedShortName, setOpenedShortName] = useState<string | null>(null);
  const [dryRunReport, setDryRunReport] = useState<DryRunReport | null>(null);
  const [activeTileId, setActiveTileId] = useState<string | null>(
    guideSelection?.kind === "tile" ? guideSelection.id : null,
  );
  // Off the history entry, so a reload starts clean.
  useEffect(() => {
    if (guideSelection || returnFocus) {
      navigate(".", { replace: true, state: null });
    }
  }, [guideSelection, returnFocus, navigate]);
  // P14 — walkthrough toggle (default on; persisted to localStorage).
  const [walkthrough, setWalkthrough] = useState<boolean>(() =>
    readWalkthroughPref(),
  );
  const reviewState = useReviewState();
  const setReviewState = useReviewStateSet();
  const clearReviewState = useReviewStateClear();
  // FP24-O: Clear-all is destructive (cart has no undo) — coding-
  // standards § 4 mandates AlertDialog confirm for destructive ops.
  const [clearAllOpen, setClearAllOpen] = useState(false);

  const config = useConfig();
  const patch = useConfigPatch();
  const sessions = useSessions();
  const upsertSession = useSessionUpsert();
  const alternatives = useAlternatives(openedShortName);
  const versionChoice = useVersionChoice(cart, returnFocus);
  const launch = useLaunchGame();
  const facets = useFacets();
  const setupCheck = useSetupCheck();
  const dryRun = useDryRun();
  const validateCart = useValidateCart();
  const copySession = useCopySession();

  const layout = (config.data?.ui.layout ?? "masonry") as LayoutName;
  const theme = (config.data?.ui.theme ?? "dark") as ThemeName;
  const activeSession = sessions.data?.active ?? null;

  const query: GamesQuery = {
    page: 1,
    pageSize: 200,
    search: filters.search,
    yearFrom: filters.yearRange[0],
    yearTo: filters.yearRange[1],
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
  const games = useGames(query);
  // FP24-V: stable refs so downstream useMemo/useEffect deps don't
  // re-run on every render. games.data flips reference on each fetch
  // resolution; the inner items/total references are already stable
  // per react-query's cached result.
  const cards: GameCard[] = useMemo(
    () => games.data?.items ?? [],
    [games.data],
  );
  const total = games.data?.total ?? 0;

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

  const openedWinner = useMemo<GameCard | null>(
    () =>
      openedShortName
        ? (cards.find((c) => c.short_name === openedShortName) ?? null)
        : null,
    [openedShortName, cards],
  );

  const handleLayout = (next: LayoutName) => {
    if (!config.data) return;
    patch.mutate({ ui: { ...config.data.ui, layout: next } });
  };
  const handleTheme = (next: ThemeName) => {
    if (!config.data) return;
    patch.mutate({ ui: { ...config.data.ui, theme: next } });
  };

  // FP24-LL: toggling a tile off must NOT wipe non-tile-driven filter
  // state (search box, letter, the various "only X" toggles). Reset
  // only the fields the tile owns (publisher / developer / genre /
  // yearRange) — everything else stays put.
  const handleTileSelect = (tileId: string) => {
    const tile = strings.library.featured.tiles.find((t) => t.id === tileId);
    if (!tile) return;
    if (activeTileId === tileId) {
      setActiveTileId(null);
      setFilters((prev) => ({
        ...prev,
        publisher: null,
        developer: null,
        genre: null,
        yearRange: DEFAULT_FILTERS.yearRange,
      }));
      return;
    }
    setActiveTileId(tileId);
    setFilters((prev) => filtersForTile(tile, prev));
  };

  const clearFilters = () => {
    setActiveTileId(null);
    setFilters(DEFAULT_FILTERS);
  };

  // FP24-M + S: handleBulkAdd promises "Add all N" where N is the
  // filter-result total — but the loaded `cards` slice is at most one
  // page (pageSize=200). Iterate the same filter at the backend's
  // page_size=500 cap until we've covered `total`, then `addAll`.
  // Surfaces MAX_CART_SIZE truncation as a toast so the user knows
  // some items didn't fit.
  const handleBulkAdd = async () => {
    const PAGE_SIZE = 500;
    const collected: string[] = [];
    const targetTotal = Math.min(total, MAX_CART_SIZE);
    let page = 1;
    while (collected.length < targetTotal) {
      const pageQuery: GamesQuery = { ...query, page, pageSize: PAGE_SIZE };
      let pageData: GamesPage;
      try {
        pageData = await apiRequest<GamesPage>(
          `/api/games?${toQueryString(pageQuery)}`,
          GamesPageSchema,
        );
      } catch (err) {
        toastApiError(err);
        return;
      }
      collected.push(...pageData.items.map((c) => c.short_name));
      if (pageData.items.length === 0) break;
      page += 1;
    }
    const { truncated } = cart.addAll(collected);
    if (truncated > 0) {
      toast.warning(strings.library.cart.maxCartReachedToast(MAX_CART_SIZE));
    }
  };

  // mame-curator-1148: add to an existing playlist, as the guide does. CANCEL
  // made the server refuse every copy once a playlist existed.
  const conflictStrategy = "APPEND";

  // P15: dry-run reads from cart.items (with chosenVariant substitution).
  const handleDryRun = () => {
    if (cart.items.length === 0) return;
    dryRun.mutate(
      {
        selected_names: cart.items.map((i) => i.chosenVariant ?? i.shortName),
        conflict_strategy: conflictStrategy,
        append_decisions: {},
      },
      { onSuccess: setDryRunReport, onError: toastApiError },
    );
  };

  const handleCopy = () => {
    if (cart.items.length === 0) return;
    // What is checked is what is sent: the server refuses a whole copy over a
    // name it does not hold, so a stale variant is dropped and said here too.
    const nameOf = (i: CartItem) => i.chosenVariant ?? i.shortName;
    validateCart.mutate(
      { short_names: cart.items.map(nameOf) },
      {
        onSuccess: ({ existing, missing, setupRequired }) => {
          // With no game list, every name is "missing" and none of them has
          // gone. Taking them out would empty the saved cart.
          if (setupRequired) {
            toast.error(strings.errors.byCode.copy_setup_required);
            return;
          }
          if (missing.length > 0) {
            toast.warning(
              strings.library.cart.validateDroppedToast(missing.length),
            );
            const gone = new Set(missing);
            for (const item of cart.items) {
              if (gone.has(nameOf(item))) cart.remove(item.shortName);
            }
          }
          if (existing.length === 0) return;
          copySession.start(
            {
              selected_names: [...existing],
              conflict_strategy: conflictStrategy,
              append_decisions: {},
            },
            { onError: toastApiError },
          );
        },
        onError: toastApiError,
      },
    );
  };

  // P15 D9: what a copy's end does to the cart, per config.ui.cart_clear_on_copy,
  // and whether the modal still has anything to say. A lost stream's outcome is
  // not known, so it does neither. Waits for the config: until it loads, the
  // user may be one who chose `never`.
  // FP24-T: cart and copySession.reset are stable useCallback refs out of
  // useCart / useCopySession, so omitting them from the dep array is
  // intentional — including them would re-run this effect on every cart
  // mutation (cart.clear changes identity if cart re-renders) and the
  // policy logic only wants to react to outcome and policy changes.
  const copyEnd = copySession.state ? copyOutcome(copySession.state) : null;
  const clearPolicy = config.data?.ui.cart_clear_on_copy;
  useEffect(() => {
    if (
      !clearPolicy ||
      !copyEnd ||
      copyEnd === "active" ||
      copyEnd === "lost"
    ) {
      return;
    }
    // mame-curator-1158: a copy taken up on opening may be the guide's, so
    // its end is no reason to empty the cart.
    if (
      !copySession.state?.reattached &&
      (clearPolicy === "always" ||
        (clearPolicy === "on_success" && copyEnd === "complete"))
    ) {
      cart.clear();
    }
    // mame-curator-1164: BIOS warnings stay on screen until the user closes them.
    const warned = (copySession.state?.warnings.length ?? 0) > 0;
    if (copyEnd === "complete" && clearPolicy !== "never" && !warned) {
      toast.success(strings.guide.copying.finishedHeading);
      copySession.reset();
    } else if (copyEnd === "stopped" && clearPolicy === "always") {
      copySession.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [copyEnd, clearPolicy]);

  // FP24-G: surface the localStorage-unavailable state as a toast so
  // the user knows their cart won't persist. Toast fires once on the
  // false → true edge; the hook keeps the flag latched for the rest
  // of the session so subsequent cart edits don't re-toast.
  useEffect(() => {
    if (cart.isStorageBroken) {
      toast.warning(strings.library.cart.storageUnavailableToast);
    }
  }, [cart.isStorageBroken]);

  const handleSaveSession = (name: string) => {
    if (!config.data) {
      toast.error(strings.library.sessionNotSaved);
      return;
    }
    const session: Session = {
      include_year_range: filters.yearRange,
      include_genres: config.data.filters.preferred_genres,
      include_publishers: config.data.filters.preferred_publishers,
      include_developers: config.data.filters.preferred_developers,
    };
    upsertSession.mutate(
      { name, session },
      {
        onSuccess: () => toast.success(strings.library.sessionSaved(name)),
        onError: toastApiError,
      },
    );
  };

  return {
    filters,
    setFilters,
    openedShortName,
    setOpenedShortName,
    dryRunReport,
    setDryRunReport,
    activeTileId,
    walkthrough,
    setWalkthrough,
    reviewState,
    setReviewState,
    clearReviewState,
    clearAllOpen,
    setClearAllOpen,
    config,
    facets,
    activeSession,
    alternatives,
    versionChoice,
    launch,
    setupCheck,
    validateCart,
    copySession,
    layout,
    theme,
    cards,
    total,
    tileCounts,
    openedWinner,
    games,
    handleLayout,
    handleTheme,
    handleTileSelect,
    clearFilters,
    handleBulkAdd,
    handleDryRun,
    handleCopy,
    handleSaveSession,
  };
}
