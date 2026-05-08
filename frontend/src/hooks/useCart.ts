import { useCallback, useMemo, useState } from 'react'

export interface CartItem {
  shortName: string
  chosenVariant?: string
}

// FP24-S: addAll returns a per-call report so the caller can fire
// strings.library.cart.maxCartReachedToast when the input was
// truncated. `truncated` is the number of input items dropped.
export interface AddAllReport {
  added: number
  truncated: number
}

export interface UseCartResult {
  items: CartItem[]
  has: (shortName: string) => boolean
  add: (shortName: string, variant?: string) => void
  remove: (shortName: string) => void
  addAll: (shortNames: string[]) => AddAllReport
  setVariant: (shortName: string, variant: string | undefined) => void
  clear: () => void
  totalBytes: number
  // FP24-G: caller toggles strings.library.cart.storageUnavailableToast
  // off this flag once the cart write throws. The flag stays true for
  // the rest of the session — re-trying after a quota error wouldn't
  // help and would re-toast on every cart change.
  isStorageBroken: boolean
}

export const MAX_CART_SIZE = 10000
export const CART_STORAGE_KEY = 'mame-curator:cart:v1'

function readInitial(): CartItem[] {
  try {
    const raw = localStorage.getItem(CART_STORAGE_KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter(
      (i): i is CartItem =>
        i !== null &&
        typeof i === 'object' &&
        typeof (i as CartItem).shortName === 'string',
    )
  } catch {
    return []
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
  const [items, setItems] = useState<CartItem[]>(readInitial)
  // FP24-G: state (not ref) so the flag flip triggers a re-render and
  // the consuming component sees the toast-trigger transition.
  const [isStorageBroken, setIsStorageBroken] = useState(false)

  // FP24-G: persistence runs inline at each mutation site rather than
  // in a useEffect, so the catch can call setIsStorageBroken without
  // tripping eslint's react-hooks/set-state-in-effect rule. Each
  // mutator computes its `next` value, stores it, and persists.
  const persist = useCallback((next: CartItem[]) => {
    try {
      localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(next))
    } catch {
      // Quota exceeded, private browsing, etc. Degrade to in-memory only.
      setIsStorageBroken(true)
    }
  }, [])

  const has = useCallback(
    (shortName: string) => items.some((i) => i.shortName === shortName),
    [items],
  )

  const add = useCallback(
    (shortName: string, variant?: string) => {
      setItems((prev) => {
        if (prev.some((i) => i.shortName === shortName)) return prev
        if (prev.length >= MAX_CART_SIZE) return prev
        const item: CartItem = { shortName }
        if (variant !== undefined) item.chosenVariant = variant
        const next = [...prev, item]
        persist(next)
        return next
      })
    },
    [persist],
  )

  const remove = useCallback(
    (shortName: string) => {
      setItems((prev) => {
        const next = prev.filter((i) => i.shortName !== shortName)
        if (next.length === prev.length) return prev
        persist(next)
        return next
      })
    },
    [persist],
  )

  // FP24-S: returns {added, truncated} so the caller can fire the
  // maxCartReachedToast on truncation. `added` is the actual delta
  // after dedup + cap; `truncated` is the count of input items
  // dropped because the cap was reached.
  const addAll = useCallback(
    (shortNames: string[]): AddAllReport => {
      let added = 0
      let truncated = 0
      setItems((prev) => {
        const seen = new Set(prev.map((i) => i.shortName))
        const merged = [...prev]
        for (const name of shortNames) {
          if (merged.length >= MAX_CART_SIZE) {
            // Every remaining input from this point is dropped. Count
            // them all (including dups) so the toast tells the truth
            // about how many user-supplied entries we lost.
            truncated += shortNames.length - shortNames.indexOf(name)
            break
          }
          if (seen.has(name)) continue
          merged.push({ shortName: name })
          seen.add(name)
          added += 1
        }
        if (merged.length !== prev.length) persist(merged)
        return merged
      })
      return { added, truncated }
    },
    [persist],
  )

  const setVariant = useCallback(
    (shortName: string, variant: string | undefined) => {
      setItems((prev) => {
        if (!prev.some((i) => i.shortName === shortName)) return prev
        const next = prev.map((i) => {
          if (i.shortName !== shortName) return i
          if (variant === undefined) {
            const { chosenVariant: _unused, ...rest } = i
            return rest
          }
          return { ...i, chosenVariant: variant }
        })
        persist(next)
        return next
      })
    },
    [persist],
  )

  const clear = useCallback(() => {
    setItems([])
    persist([])
  }, [persist])

  const totalBytes = useMemo(() => 0, [])

  return {
    items,
    has,
    add,
    remove,
    addAll,
    setVariant,
    clear,
    totalBytes,
    isStorageBroken,
  }
}
