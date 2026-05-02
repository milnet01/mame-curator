import { useEffect } from 'react'

export interface KeyBinding {
  /** Either a single key (e.g. "k", "Escape", "?") or a chord like "g l". */
  combo: string
  /** Key event handler. The handler decides whether to preventDefault. */
  handler: (e: KeyboardEvent) => void
  /** Match Cmd (macOS) or Ctrl (others). */
  meta?: boolean
}

const PENDING_CHORD_TIMEOUT_MS = 1000

function isModifiable(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  const tag = target.tagName
  return (
    tag === 'INPUT' ||
    tag === 'TEXTAREA' ||
    tag === 'SELECT' ||
    target.isContentEditable
  )
}

/**
 * Register one or more global keyboard shortcuts for the lifetime of the
 * caller component. Chords use space-separated keys (e.g. `g l` for "go
 * library"); a chord stays armed for {@link PENDING_CHORD_TIMEOUT_MS}.
 *
 * Bindings registered while a typing-capable element is focused are
 * skipped, EXCEPT when `meta: true` and the modifier key is held — Cmd-K
 * still opens the palette while typing in the search box.
 */
export function useKeyboard(bindings: KeyBinding[]) {
  useEffect(() => {
    let pendingChord: string | null = null
    let pendingTimer: ReturnType<typeof setTimeout> | null = null

    const clearPending = () => {
      pendingChord = null
      if (pendingTimer) {
        clearTimeout(pendingTimer)
        pendingTimer = null
      }
    }

    const onKeyDown = (e: KeyboardEvent) => {
      const editing = isModifiable(e.target)

      for (const binding of bindings) {
        if (binding.meta) {
          if (!(e.metaKey || e.ctrlKey)) continue
          if (e.key.toLowerCase() === binding.combo.toLowerCase()) {
            binding.handler(e)
            return
          }
          continue
        }

        if (editing) continue

        const parts = binding.combo.split(' ')
        if (parts.length === 1) {
          if (e.key === binding.combo) {
            binding.handler(e)
            return
          }
        } else {
          if (pendingChord === parts[0] && e.key === parts[1]) {
            clearPending()
            binding.handler(e)
            return
          }
          if (pendingChord === null && e.key === parts[0]) {
            pendingChord = parts[0]!
            pendingTimer = setTimeout(clearPending, PENDING_CHORD_TIMEOUT_MS)
          }
        }
      }
    }

    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      clearPending()
    }
  }, [bindings])
}
