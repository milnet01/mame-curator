import { useCallback, useMemo, useRef, useState } from "react";

export interface CartItem {
  shortName: string;
  chosenVariant?: string;
}

// FP24-S: addAll returns a per-call report so the caller can fire
// strings.library.cart.maxCartReachedToast when the input was
// truncated. `truncated` is the number of input items dropped.
export interface AddAllReport {
  added: number;
  truncated: number;
}

/** mame-curator-1234 (CR-09-9): what adding one game did. `full` is the cart
 *  at MAX_CART_SIZE refusing it, which the caller tells the user. */
export type AddOutcome = "added" | "held" | "full";

export interface UseCartResult {
  items: CartItem[];
  has: (shortName: string) => boolean;
  add: (shortName: string, variant?: string) => AddOutcome;
  remove: (shortName: string) => void;
  toggle: (shortName: string) => AddOutcome | "removed";
  addAll: (shortNames: string[]) => AddAllReport;
  setVariant: (shortName: string, variant: string | undefined) => void;
  clear: () => void;
  totalBytes: number;
  // FP24-G: caller toggles strings.library.cart.storageUnavailableToast
  // off this flag once the cart write throws. The flag stays true for
  // the rest of the session — re-trying after a quota error wouldn't
  // help and would re-toast on every cart change.
  isStorageBroken: boolean;
}

export const MAX_CART_SIZE = 10000;

/** mame-curator-1188: an entry stands for the game by the name it was added
 *  under and by the version chosen for it, which is the card then on show. */
function holds(item: CartItem, name: string): boolean {
  return item.shortName === name || item.chosenVariant === name;
}
export const CART_STORAGE_KEY = "mame-curator:cart:v1";

function readInitial(): CartItem[] {
  try {
    const raw = localStorage.getItem(CART_STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    // FP24-R: validate chosenVariant type as well — a hand-edited
    // localStorage entry like `{shortName: "sf2", chosenVariant: 123}`
    // would otherwise reach the rest of the code as a non-string and
    // crash downstream `.map((i) => i.chosenVariant ?? i.shortName)`.
    return parsed.filter((i): i is CartItem => {
      if (i === null || typeof i !== "object") return false;
      const candidate = i as Record<string, unknown>;
      if (typeof candidate.shortName !== "string") return false;
      const variant = candidate.chosenVariant;
      return variant === undefined || typeof variant === "string";
    });
  } catch {
    return [];
  }
}

/**
 * P15 § 4.1 cart hook.
 *
 * Working pre-copy intent, frontend-only, localStorage-backed.
 * No server resource; no concurrency story (per-tab independent).
 *
 * `totalBytes` is reserved for future use; today it stays 0.
 * The server-authoritative bottom-bar number lives on
 * /api/games's total_bytes (filtered slice, not cart slice).
 * Showing cart-only bytes would need either a new endpoint or
 * a client-side cache of byte sums per shortname — out of scope
 * for v1.
 */
export function useCart(): UseCartResult {
  const [items, setItems] = useState<CartItem[]>(readInitial);
  // FP24-G: state (not ref) so the flag flip triggers a re-render and
  // the consuming component sees the toast-trigger transition.
  const [isStorageBroken, setIsStorageBroken] = useState(false);

  // FP24-G: persistence runs inline at each mutation site rather than
  // in a useEffect, so the catch can call setIsStorageBroken without
  // tripping eslint's react-hooks/set-state-in-effect rule.
  const persist = useCallback((next: CartItem[]) => {
    try {
      localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(next));
    } catch {
      // Quota exceeded, private browsing, etc. Degrade to in-memory only.
      setIsStorageBroken(true);
    }
  }, []);

  // mame-curator-1233: each mutator works out `next` from the latest list,
  // including changes React has not applied yet, and then stores it. A
  // state updater is no place for that: React may run it late or twice, so
  // addAll's report could come back empty or doubled.
  const latest = useRef(items);
  const commit = useCallback(
    (next: CartItem[]) => {
      latest.current = next;
      setItems(next);
      persist(next);
    },
    [persist],
  );

  const has = useCallback(
    (shortName: string) => items.some((i) => holds(i, shortName)),
    [items],
  );

  const add = useCallback(
    (shortName: string, variant?: string): AddOutcome => {
      const prev = latest.current;
      if (prev.some((i) => holds(i, shortName))) return "held";
      if (prev.length >= MAX_CART_SIZE) return "full";
      const item: CartItem = { shortName };
      if (variant !== undefined) item.chosenVariant = variant;
      commit([...prev, item]);
      return "added";
    },
    [commit],
  );

  const remove = useCallback(
    (shortName: string) => {
      const prev = latest.current;
      const next = prev.filter((i) => i.shortName !== shortName);
      if (next.length !== prev.length) commit(next);
    },
    [commit],
  );

  // The game card's button: removes the entry standing for the game shown,
  // by either of its names, or adds the game.
  const toggle = useCallback(
    (shortName: string): AddOutcome | "removed" => {
      const prev = latest.current;
      const next = prev.filter((i) => !holds(i, shortName));
      if (next.length === prev.length) return add(shortName);
      commit(next);
      return "removed";
    },
    [add, commit],
  );

  // FP24-S: returns {added, truncated} so the caller can fire the
  // maxCartReachedToast on truncation. `added` is the actual delta
  // after dedup + cap; `truncated` is the count of input items
  // dropped because the cap was reached.
  const addAll = useCallback(
    (shortNames: string[]): AddAllReport => {
      const prev = latest.current;
      const seen = new Set(
        prev.flatMap((i) =>
          i.chosenVariant ? [i.shortName, i.chosenVariant] : [i.shortName],
        ),
      );
      const merged = [...prev];
      let truncated = 0;
      for (const [index, name] of shortNames.entries()) {
        if (merged.length >= MAX_CART_SIZE) {
          // Every remaining input from this point is dropped. Count
          // them all (including dups) so the toast tells the truth
          // about how many user-supplied entries we lost.
          truncated = shortNames.length - index;
          break;
        }
        if (seen.has(name)) continue;
        merged.push({ shortName: name });
        seen.add(name);
      }
      const added = merged.length - prev.length;
      if (added > 0) commit(merged);
      return { added, truncated };
    },
    [commit],
  );

  const setVariant = useCallback(
    (shortName: string, variant: string | undefined) => {
      const prev = latest.current;
      if (!prev.some((i) => i.shortName === shortName)) return;
      commit(
        prev.map((i) => {
          if (i.shortName !== shortName) return i;
          if (variant === undefined) {
            const { chosenVariant: _unused, ...rest } = i;
            return rest;
          }
          return { ...i, chosenVariant: variant };
        }),
      );
    },
    [commit],
  );

  const clear = useCallback(() => commit([]), [commit]);

  const totalBytes = useMemo(() => 0, []);

  return {
    items,
    has,
    add,
    remove,
    toggle,
    addAll,
    setVariant,
    clear,
    totalBytes,
    isStorageBroken,
  };
}
