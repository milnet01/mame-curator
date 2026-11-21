/**
 * The Library grid's keys (mame-curator-1234, CR-09-12: out of
 * `LibraryGrid.tsx`, over its size cap). Arrows, j/k, Home and End move
 * the active card; Enter or o opens it; r, s and ? set its review state,
 * and in walkthrough move on to the next pending game, loading the next
 * page to look in when this one has none.
 */
import { useCallback, useEffect, useRef } from "react";
import { toast } from "sonner";
import { strings } from "@/strings";
import type {
  GameCard as GameCardType,
  ReviewStateValue,
  StateView,
} from "@/api/types";

const KEY_TO_STATE: Record<string, ReviewStateValue> = {
  r: "reviewed",
  s: "skipped",
  "?": "needs-decision",
};

interface GridKeysArgs {
  cards: GameCardType[];
  columns: number;
  activeIndex: number;
  move: (delta: number) => void;
  setActive: (index: number) => void;
  /** The index of the next pending card from `startIndex`, or null. */
  focusNextPending: (startIndex: number) => number | null;
  hasMore: boolean;
  onLoadMore?: () => void;
  onOpen: (card: GameCardType) => void;
  reviewState?: StateView;
  onSetReviewState?: (shortName: string, state: ReviewStateValue) => void;
  onClearReviewState?: (shortName: string) => void;
  walkthrough: boolean;
}

/** Returns the grid's `onKeyDown` handler. */
export function useLibraryGridKeys({
  cards,
  columns,
  activeIndex,
  move,
  setActive,
  focusNextPending,
  hasMore,
  onLoadMore,
  onOpen,
  reviewState,
  onSetReviewState,
  onClearReviewState,
  walkthrough,
}: GridKeysArgs) {
  // P14 walkthrough: the next pending game may be on a page not loaded yet.
  // `advanceFrom` holds where the search starts until that page lands.
  const advanceFrom = useRef<number | null>(null);
  const advance = useCallback(
    (startIndex: number) => {
      const next = focusNextPending(startIndex);
      if (next !== null) {
        advanceFrom.current = null;
        setActive(next);
      } else if (hasMore) {
        advanceFrom.current = startIndex;
        onLoadMore?.();
      } else {
        advanceFrom.current = null;
        toast.success(strings.library.walkthroughCaughtUp);
      }
    },
    [focusNextPending, hasMore, onLoadMore, setActive],
  );
  // `advance` changes when a page lands, so the search goes on from there.
  useEffect(() => {
    if (advanceFrom.current !== null) advance(advanceFrom.current);
  }, [advance]);

  return useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      // Ctrl+R, Ctrl+S, Ctrl+K and the like belong to the browser or palette.
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      // Any key the grid acts on ends a walkthrough search still waiting for
      // a page, so the page landing cannot pull focus from where it went.
      advanceFrom.current = null;
      switch (e.key) {
        case "ArrowDown":
        case "j":
          e.preventDefault();
          move(columns);
          break;
        case "ArrowUp":
        case "k":
          e.preventDefault();
          move(-columns);
          break;
        case "ArrowRight":
          e.preventDefault();
          move(1);
          break;
        case "ArrowLeft":
          e.preventDefault();
          move(-1);
          break;
        case "Home":
          e.preventDefault();
          setActive(0);
          break;
        case "End":
          e.preventDefault();
          setActive(Math.max(0, cards.length - 1));
          break;
        case "Enter":
        case "o": {
          // A card and its Add button answer Enter themselves.
          if (e.key === "Enter" && e.target !== e.currentTarget) break;
          const card = cards[activeIndex];
          if (card) {
            e.preventDefault();
            onOpen(card);
          }
          break;
        }
        case "r":
        case "s":
        case "?": {
          // P14 chunk 12 — toggle on same-key press; walkthrough auto-advance.
          if (!onSetReviewState) break;
          const card = cards[activeIndex];
          if (!card) break;
          e.preventDefault();
          const target = KEY_TO_STATE[e.key]!;
          const current = reviewState?.entries[card.short_name];
          const startedAt = activeIndex;
          if (current === target) {
            // Toggle back to pending; no walkthrough advance (the just-
            // cleared card is itself pending now).
            onClearReviewState?.(card.short_name);
          } else {
            onSetReviewState(card.short_name, target);
            if (walkthrough) advance(startedAt + 1);
          }
          break;
        }
      }
    },
    [
      activeIndex,
      advance,
      cards,
      columns,
      move,
      onClearReviewState,
      onOpen,
      onSetReviewState,
      reviewState,
      setActive,
      walkthrough,
    ],
  );
}
