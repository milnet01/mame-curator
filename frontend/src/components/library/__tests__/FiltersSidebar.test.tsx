import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { FiltersSidebar } from '../FiltersSidebar'
import { baseFiltersValue } from '@/test/fixtures'

// DS04 T3.1: removed redundant `afterEach(() => cleanup())` — vitest
// `globals: true` enables RTL's auto-cleanup.
// FP05 (2026-05-18): the 11-field neutral filters value lives in
// `@/test/fixtures` so a future field addition fixes every consumer at
// the same time.

describe('FiltersSidebar', () => {
  it('renders Switch (not Checkbox) for every binary preference', () => {
    render(
      <FiltersSidebar
        value={baseFiltersValue}
        onChange={() => {}}
        onSaveSession={() => {}}
      />,
    )
    expect(screen.queryAllByRole('checkbox')).toHaveLength(0)
    expect(screen.getAllByRole('switch').length).toBeGreaterThanOrEqual(4)
  })

  it('debounces the search input by ~200ms before calling onChange', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    try {
      const onChange = vi.fn()
      render(
        <FiltersSidebar
          value={baseFiltersValue}
          onChange={onChange}
          onSaveSession={() => {}}
        />,
      )
      const input = screen.getByLabelText(/search/i)
      await userEvent.type(input, 'pacm')
      // No call before the debounce window elapses.
      expect(onChange).not.toHaveBeenCalled()
      vi.advanceTimersByTime(250)
      expect(onChange).toHaveBeenCalled()
      const lastCall = onChange.mock.calls.at(-1)?.[0] as { search: string }
      expect(lastCall.search).toBe('pacm')
    } finally {
      // try/finally so a mid-test assertion failure doesn't leak fake timers
      // into the next test in the file.
      vi.useRealTimers()
    }
  })

  it('opens the save-as-session prompt and forwards the typed name', async () => {
    const onSaveSession = vi.fn()
    render(
      <FiltersSidebar
        value={baseFiltersValue}
        onChange={() => {}}
        onSaveSession={onSaveSession}
      />,
    )
    await userEvent.click(screen.getByRole('button', { name: /save as session/i }))
    const nameInput = await screen.findByLabelText(/session name/i)
    await userEvent.type(nameInput, 'late-90s-fighters')
    await userEvent.click(screen.getByRole('button', { name: /^save$/i }))
    expect(onSaveSession).toHaveBeenCalledWith('late-90s-fighters')
  })
})
