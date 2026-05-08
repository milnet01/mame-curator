import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import { useCart, MAX_CART_SIZE } from '@/hooks/useCart'

describe('useCart', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('starts empty', () => {
    const { result } = renderHook(() => useCart())
    expect(result.current.items).toEqual([])
    expect(result.current.totalBytes).toBe(0)
  })

  it('add() appends a CartItem and persists across remounts', () => {
    const { result, rerender } = renderHook(() => useCart())
    act(() => result.current.add('pacman'))
    expect(result.current.items).toEqual([{ shortName: 'pacman' }])

    rerender()
    expect(result.current.items).toEqual([{ shortName: 'pacman' }])

    // Fresh mount reads from localStorage
    const { result: fresh } = renderHook(() => useCart())
    expect(fresh.current.items).toEqual([{ shortName: 'pacman' }])
  })

  it('add() is idempotent — duplicate shortName does not appear twice', () => {
    const { result } = renderHook(() => useCart())
    act(() => result.current.add('pacman'))
    act(() => result.current.add('pacman'))
    expect(result.current.items).toHaveLength(1)
  })

  it('has() reflects membership', () => {
    const { result } = renderHook(() => useCart())
    expect(result.current.has('pacman')).toBe(false)
    act(() => result.current.add('pacman'))
    expect(result.current.has('pacman')).toBe(true)
  })

  it('remove() drops the item', () => {
    const { result } = renderHook(() => useCart())
    act(() => result.current.add('pacman'))
    act(() => result.current.remove('pacman'))
    expect(result.current.items).toEqual([])
  })

  it('addAll() merges, dedupes, preserves existing order', () => {
    const { result } = renderHook(() => useCart())
    act(() => result.current.add('pacman'))
    act(() => result.current.addAll(['pacmanf', 'pacman', '1942']))
    expect(result.current.items.map((i) => i.shortName)).toEqual([
      'pacman',
      'pacmanf',
      '1942',
    ])
  })

  it('addAll() truncates at MAX_CART_SIZE', () => {
    const { result } = renderHook(() => useCart())
    const huge = Array.from({ length: MAX_CART_SIZE + 100 }, (_, i) => `g${i}`)
    act(() => result.current.addAll(huge))
    expect(result.current.items).toHaveLength(MAX_CART_SIZE)
  })

  // FP24-S: addAll must report how many items were actually added vs
  // dropped to truncation so the caller can fire maxCartReachedToast.
  it('addAll() returns {added, truncated} so callers can toast', () => {
    const { result } = renderHook(() => useCart())
    let report = { added: -1, truncated: -1 }
    act(() => {
      report = result.current.addAll(
        Array.from({ length: MAX_CART_SIZE + 7 }, (_, i) => `g${i}`),
      )
    })
    expect(report.added).toBe(MAX_CART_SIZE)
    expect(report.truncated).toBe(7)
  })

  it('addAll() reports truncated:0 when within bounds', () => {
    const { result } = renderHook(() => useCart())
    let report = { added: -1, truncated: -1 }
    act(() => {
      report = result.current.addAll(['a', 'b', 'c'])
    })
    expect(report.added).toBe(3)
    expect(report.truncated).toBe(0)
  })

  it('setVariant() updates chosenVariant on an existing entry', () => {
    const { result } = renderHook(() => useCart())
    act(() => result.current.add('1942'))
    act(() => result.current.setVariant('1942', '1942j'))
    expect(result.current.items[0]).toEqual({ shortName: '1942', chosenVariant: '1942j' })

    // Pass undefined to clear
    act(() => result.current.setVariant('1942', undefined))
    expect(result.current.items[0]).toEqual({ shortName: '1942' })
  })

  it('setVariant() on missing item is a no-op', () => {
    const { result } = renderHook(() => useCart())
    act(() => result.current.setVariant('ghost', 'ghostj'))
    expect(result.current.items).toEqual([])
  })

  it('clear() empties the cart', () => {
    const { result } = renderHook(() => useCart())
    act(() => result.current.addAll(['a', 'b', 'c']))
    act(() => result.current.clear())
    expect(result.current.items).toEqual([])
  })

  it('falls back to in-memory when localStorage write throws', () => {
    const setItem = Storage.prototype.setItem
    Storage.prototype.setItem = () => {
      throw new DOMException('QuotaExceededError', 'QuotaExceededError')
    }
    try {
      const { result } = renderHook(() => useCart())
      // Should not throw despite storage failure
      expect(() => act(() => result.current.add('pacman'))).not.toThrow()
      expect(result.current.items).toEqual([{ shortName: 'pacman' }])
    } finally {
      Storage.prototype.setItem = setItem
    }
  })

  // FP24-G: caller needs visibility into the "storage is broken" state
  // to fire strings.library.cart.storageUnavailableToast — previously
  // the useRef was set internally but never returned so the toast
  // never fired even though the spec mandates it.
  it('isStorageBroken flips true after a write throws', () => {
    const setItem = Storage.prototype.setItem
    Storage.prototype.setItem = () => {
      throw new DOMException('QuotaExceededError', 'QuotaExceededError')
    }
    try {
      const { result } = renderHook(() => useCart())
      expect(result.current.isStorageBroken).toBe(false)
      act(() => result.current.add('pacman'))
      expect(result.current.isStorageBroken).toBe(true)
    } finally {
      Storage.prototype.setItem = setItem
    }
  })

  it('isStorageBroken stays false on healthy storage', () => {
    const { result } = renderHook(() => useCart())
    act(() => result.current.add('pacman'))
    expect(result.current.isStorageBroken).toBe(false)
  })
})
