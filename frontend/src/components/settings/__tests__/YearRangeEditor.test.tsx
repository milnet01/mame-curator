import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, cleanup, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { YearRangeEditor } from '../YearRangeEditor'

afterEach(() => cleanup())

const bounds = { minYear: 1971, maxYear: 2026 }

describe('YearRangeEditor', () => {
  it('renders both fields with current values when set', () => {
    render(
      <YearRangeEditor
        before={1990}
        after={2010}
        onBeforeChange={() => {}}
        onAfterChange={() => {}}
        {...bounds}
      />,
    )
    expect(screen.getByLabelText('Drop games before year')).toHaveValue(1990)
    expect(screen.getByLabelText('Drop games after year')).toHaveValue(2010)
  })

  it('disables both inputs when both values are null', () => {
    render(
      <YearRangeEditor
        before={null}
        after={null}
        onBeforeChange={() => {}}
        onAfterChange={() => {}}
        {...bounds}
      />,
    )
    expect(screen.getByLabelText('Drop games before year')).toBeDisabled()
    expect(screen.getByLabelText('Drop games after year')).toBeDisabled()
  })

  it('exposes both bounds switches via role=switch', () => {
    render(
      <YearRangeEditor
        before={null}
        after={null}
        onBeforeChange={() => {}}
        onAfterChange={() => {}}
        {...bounds}
      />,
    )
    const switches = screen.getAllByRole('switch')
    expect(switches).toHaveLength(2)
    expect(switches[0]).toHaveAttribute('aria-checked', 'false')
  })

  it('fires onBeforeChange with the typed year', () => {
    const onBeforeChange = vi.fn()
    render(
      <YearRangeEditor
        before={1990}
        after={null}
        onBeforeChange={onBeforeChange}
        onAfterChange={() => {}}
        {...bounds}
      />,
    )
    const input = screen.getByLabelText('Drop games before year')
    fireEvent.change(input, { target: { value: '2000' } })
    expect(onBeforeChange).toHaveBeenLastCalledWith(2000)
  })

  it('fires onBeforeChange(null) when the before-switch is toggled off', async () => {
    const onBeforeChange = vi.fn()
    render(
      <YearRangeEditor
        before={1990}
        after={null}
        onBeforeChange={onBeforeChange}
        onAfterChange={() => {}}
        {...bounds}
      />,
    )
    const switches = screen.getAllByRole('switch')
    await userEvent.click(switches[0])
    expect(onBeforeChange).toHaveBeenCalledWith(null)
  })

  it('fires onBeforeChange(minYear) when the before-switch is toggled on', async () => {
    const onBeforeChange = vi.fn()
    render(
      <YearRangeEditor
        before={null}
        after={null}
        onBeforeChange={onBeforeChange}
        onAfterChange={() => {}}
        {...bounds}
      />,
    )
    const switches = screen.getAllByRole('switch')
    await userEvent.click(switches[0])
    expect(onBeforeChange).toHaveBeenCalledWith(1971)
  })

  it('fires onAfterChange(maxYear) when the after-switch is toggled on', async () => {
    const onAfterChange = vi.fn()
    render(
      <YearRangeEditor
        before={null}
        after={null}
        onBeforeChange={() => {}}
        onAfterChange={onAfterChange}
        {...bounds}
      />,
    )
    const switches = screen.getAllByRole('switch')
    await userEvent.click(switches[1])
    expect(onAfterChange).toHaveBeenCalledWith(2026)
  })

  it('sets min and max attributes on both inputs', () => {
    render(
      <YearRangeEditor
        before={1990}
        after={2010}
        onBeforeChange={() => {}}
        onAfterChange={() => {}}
        {...bounds}
      />,
    )
    const before = screen.getByLabelText('Drop games before year')
    const after = screen.getByLabelText('Drop games after year')
    expect(before).toHaveAttribute('min', '1971')
    expect(before).toHaveAttribute('max', '2026')
    expect(after).toHaveAttribute('min', '1971')
    expect(after).toHaveAttribute('max', '2026')
  })

  it('emits null when an enabled input is cleared', () => {
    const onBeforeChange = vi.fn()
    render(
      <YearRangeEditor
        before={1990}
        after={null}
        onBeforeChange={onBeforeChange}
        onAfterChange={() => {}}
        {...bounds}
      />,
    )
    const input = screen.getByLabelText('Drop games before year')
    fireEvent.change(input, { target: { value: '' } })
    expect(onBeforeChange).toHaveBeenLastCalledWith(null)
  })
})
