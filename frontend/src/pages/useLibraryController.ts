/**
 * `LibraryPage` controller hook (mame-curator-1077 — split the page
 * under the §2 frontend file-size hard cap of 350 lines). Holds the
 * page's non-render logic so `LibraryPage.tsx` stays a thin view. The
 * games list, Add all, and dry run and copy are their own hooks
 * (mame-curator-1234, CR-09-12).
 */
import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router";
import { toast } from "sonner";
import { type FilterSidebarState } from "@/components/library/FiltersSidebar";
import { useAlternatives, useLaunchGame } from "@/hooks/useAlternatives";
import { MAX_CART_SIZE, type UseCartResult } from "@/hooks/useCart";
import { useFacets } from "@/hooks/useFacets";
import {
  useReviewState,
  useReviewStateClear,
  useReviewStateSet,
} from "@/hooks/useReviewState";
import { useConfig, useConfigPatch } from "@/hooks/useConfig";
import { useSessions, useSessionUpsert } from "@/hooks/useSessions";
import { useSetupCheck } from "@/hooks/useSetupCheck";
import { toastApiError } from "@/lib/apiErrorToast";
import { strings } from "@/strings";
import type { GameCard, LayoutName, Session, ThemeName } from "@/api/types";
import {
  DEFAULT_FILTERS,
  filtersForGuideSelection,
  filtersForTile,
  readGuideSelection,
  readReturnFocus,
  readWalkthroughPref,
  saveWalkthroughPref,
} from "./libraryPageHelpers";
import { useBulkAdd } from "./useBulkAdd";
import { useLibraryCopy } from "./useLibraryCopy";
import { useLibraryGames } from "./useLibraryGames";
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
  const [walkthrough, setWalkthroughState] = useState<boolean>(() =>
    readWalkthroughPref(),
  );
  const setWalkthrough = (on: boolean) => {
    setWalkthroughState(on);
    saveWalkthroughPref(on);
  };
  const reviewState = useReviewState();
  const setReviewState = useReviewStateSet();
  const clearReviewState = useReviewStateClear();

  const config = useConfig();
  const patch = useConfigPatch();
  const sessions = useSessions();
  const upsertSession = useSessionUpsert();
  const alternatives = useAlternatives(openedShortName);
  const versionChoice = useVersionChoice(cart, returnFocus);
  const launch = useLaunchGame();
  const facets = useFacets();
  const setupCheck = useSetupCheck();
  const { query, games, cards, total, hasMore, loadMore, tileCounts } =
    useLibraryGames(filters);
  const { handleBulkAdd, bulkAdding } = useBulkAdd(cart, query, total);
  const copy = useLibraryCopy(cart, config);

  const layout = (config.data?.ui.layout ?? "masonry") as LayoutName;
  const theme = (config.data?.ui.theme ?? "dark") as ThemeName;
  const activeSession = sessions.data?.active ?? null;

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

  // mame-curator-1234 (CR-09-9): a full cart refuses one game as it does many,
  // and says so as Add all does.
  const handleToggleCart = (shortName: string) => {
    if (cart.toggle(shortName) === "full") {
      toast.warning(strings.library.cart.maxCartReachedToast(MAX_CART_SIZE));
    }
  };

  // FP24-G: surface the localStorage-unavailable state as a toast so
  // the user knows their cart won't persist. Toast fires once on the
  // false → true edge; the hook keeps the flag latched for the rest
  // of the session so subsequent cart edits don't re-toast.
  useEffect(() => {
    if (cart.isStorageBroken) {
      toast.warning(strings.library.cart.storageUnavailableToast);
    }
  }, [cart.isStorageBroken]);

  // mame-curator-1156: a session saves what is on screen now. A session holds
  // years, genres, publishers and developers only, so a search, a letter and
  // the "only" switches are not saved.
  const handleSaveSession = (name: string) => {
    const session: Session = {
      include_year_range: filters.yearRange,
      include_genres: filters.genre ? [filters.genre] : [],
      include_publishers: filters.publisher ? [filters.publisher] : [],
      include_developers: filters.developer ? [filters.developer] : [],
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
    /** mame-curator-1209: the page was opened by the guide's "Look through". */
    fromGuide: guideSelection !== null,
    ...copy,
    filters,
    setFilters,
    openedShortName,
    setOpenedShortName,
    activeTileId,
    walkthrough,
    setWalkthrough,
    reviewState,
    setReviewState,
    clearReviewState,
    config,
    facets,
    activeSession,
    alternatives,
    versionChoice,
    launch,
    setupCheck,
    layout,
    theme,
    cards,
    total,
    hasMore,
    loadMore,
    tileCounts,
    openedWinner,
    games,
    handleLayout,
    handleTheme,
    handleTileSelect,
    clearFilters,
    handleBulkAdd,
    bulkAdding,
    handleToggleCart,
    handleSaveSession,
  };
}
