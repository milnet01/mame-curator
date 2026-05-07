import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

export interface CartItem {
  shortName: string
  chosenVariant?: string
}

export interface UseCartResult {
  items: CartItem[]
  has: (shortName: string) => boolean
  add: (shortName: string, variant?: string) => void
  remove: (shortName: string) => void
  addAll: (shortNames: string[]) => void
  setVariant: (shortName: string, variant: string | undefined) => void
  clear: () => void
  totalBytes: number
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
  const storageBroken = useRef(false)

  useEffect(() => {
    if (storageBroken.current) return
    try {
      localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(items))
    } catch {
      // Quota exceeded, private browsing, etc. Degrade to in-memory only.
      storageBroken.current = true
    }
  }, [items])

  const has = useCallback(
    (shortName: string) => items.some((i) => i.shortName === shortName),
    [items],
  )

  const add = useCallback((shortName: string, variant?: string) => {
    setItems((prev) => {
      if (prev.some((i) => i.shortName === shortName)) return prev
      if (prev.length >= MAX_CART_SIZE) return prev
      const item: CartItem = { shortName }
      if (variant !== undefined) item.chosenVariant = variant
      return [...prev, item]
    })
  }, [])

  const remove = useCallback((shortName: string) => {
    setItems((prev) => prev.filter((i) => i.shortName !== shortName))
  }, [])

  const addAll = useCallback((shortNames: string[]) => {
    setItems((prev) => {
      const seen = new Set(prev.map((i) => i.shortName))
      const merged = [...prev]
      for (const name of shortNames) {
        if (merged.length >= MAX_CART_SIZE) break
        if (seen.has(name)) continue
        merged.push({ shortName: name })
        seen.add(name)
      }
      return merged
    })
  }, [])

  const setVariant = useCallback(
    (shortName: string, variant: string | undefined) => {
      setItems((prev) => {
        if (!prev.some((i) => i.shortName === shortName)) return prev
        return prev.map((i) => {
          if (i.shortName !== shortName) return i
          if (variant === undefined) {
            const { chosenVariant: _, ...rest } = i
            return rest
          }
          return { ...i, chosenVariant: variant }
        })
      })
    },
    [],
  )

  const clear = useCallback(() => setItems([]), [])

  const totalBytes = useMemo(() => 0, [])

  return { items, has, add, remove, addAll, setVariant, clear, totalBytes }
}
