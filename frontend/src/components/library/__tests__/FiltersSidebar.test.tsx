import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { FiltersSidebar } from '../FiltersSidebar'

afterEach(() => cleanup())

describe('FiltersSidebar', () => {
  it('renders Switch (not Checkbox) for every binary preference', () => {
    render(
      <FiltersSidebar
        value={{
          search: '',
          yearRange: [1980, 2010],
          letter: null,
          genre: null,
          publisher: null,
          developer: null,
          onlyContested: false,
          onlyOverridden: false,
          onlyChdMissing: false,
          onlyBiosMissing: false,
        }}
        onChange={() => {}}
        onSaveSession={() => {}}
      />,
    )
    expect(screen.queryAllByRole('checkbox')).toHaveLength(0)
    expect(screen.getAllByRole('switch').length).toBeGreaterThanOrEqual(4)
  })

  it('debounces the search input by ~200ms before calling onChange', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const onChange = vi.fn()
    render(
      <FiltersSidebar
        value={{
          search: '',
          yearRange: [1980, 2010],
          letter: null,
          genre: null,
          publisher: null,
          developer: null,
          onlyContested: false,
          onlyOverridden: false,
          onlyChdMissing: false,
          onlyBiosMissing: false,
        }}
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
    vi.useRealTimers()
  })

  it('opens the save-as-session prompt and forwards the typed name', async () => {
    const onSaveSession = vi.fn()
    render(
      <FiltersSidebar
        value={{
          search: '',
          yearRange: [1980, 2010],
          letter: null,
          genre: null,
          publisher: null,
          developer: null,
          onlyContested: false,
          onlyOverridden: false,
          onlyChdMissing: false,
          onlyBiosMissing: false,
        }}
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
