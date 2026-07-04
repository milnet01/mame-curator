import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { MediaSourceRow } from '../MediaSourceRow'
import type { SourceReadinessRow } from '@/api/types'

const noop = () => {}

function row(over: Partial<SourceReadinessRow> = {}): SourceReadinessRow {
  return {
    name: 'libretro',
    enabled: true,
    in_chain: true,
    kinds: ['boxart', 'title', 'snap'],
    license_compatible: true,
    disabled_reason: null,
    needs_config: false,
    ...over,
  }
}

describe('MediaSourceRow', () => {
  it('renders a green Active dot for an enabled source, with no reason line', () => {
    const { container } = render(
      <MediaSourceRow row={row()} onConfigure={noop} onDownloadPack={noop} onToggle={noop} />,
    )
    expect(container.querySelector('[data-state="active"]')).not.toBeNull()
    expect(container.querySelector('[data-state="disabled"]')).toBeNull()
    // enabled → disabled_reason null → no reason paragraph
    expect(screen.queryByText(/api key|not downloaded/i)).toBeNull()
  })

  it('renders a grey Disabled dot + reason line + Configure button for a disabled needs_config source', () => {
    const { container } = render(
      <MediaSourceRow
        row={row({
          name: 'mobyGames',
          enabled: false,
          needs_config: true,
          kinds: ['boxart'],
          disabled_reason: 'No API key configured.',
        })}
        onConfigure={noop}
        onDownloadPack={noop}
        onToggle={noop}
      />,
    )
    expect(container.querySelector('[data-state="disabled"]')).not.toBeNull()
    expect(screen.getByText('No API key configured.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /configure/i })).toBeInTheDocument()
  })

  it('does not render a Configure button for a disabled non-config source', () => {
    render(
      <MediaSourceRow
        row={row({ name: 'libretro', enabled: false, needs_config: false, disabled_reason: 'down' })}
        onConfigure={noop}
        onDownloadPack={noop}
        onToggle={noop}
      />,
    )
    expect(screen.queryByRole('button', { name: /configure/i })).toBeNull()
  })

  // mame-curator-1084 — per-source on/off toggle (chain membership).
  it('renders a checked toggle for an in-chain source', () => {
    render(
      <MediaSourceRow
        row={row({ name: 'arcadeDB', in_chain: true })}
        onConfigure={noop}
        onDownloadPack={noop}
        onToggle={noop}
      />,
    )
    const toggle = screen.getByRole('switch', { name: /arcadeDB/i })
    expect(toggle).toBeChecked()
    expect(toggle).toBeEnabled()
  })

  it('renders an unchecked toggle for an unconfigured source', () => {
    render(
      <MediaSourceRow
        row={row({ name: 'wikipediaImage', in_chain: false })}
        onConfigure={noop}
        onDownloadPack={noop}
        onToggle={noop}
      />,
    )
    expect(screen.getByRole('switch', { name: /wikipediaImage/i })).not.toBeChecked()
  })

  it('calls onToggle(name, false) when an in-chain source is switched off', async () => {
    const onToggle = vi.fn()
    const user = userEvent.setup()
    render(
      <MediaSourceRow
        row={row({ name: 'arcadeDB', in_chain: true })}
        onConfigure={noop}
        onDownloadPack={noop}
        onToggle={onToggle}
      />,
    )
    await user.click(screen.getByRole('switch', { name: /arcadeDB/i }))
    expect(onToggle).toHaveBeenCalledWith('arcadeDB', false)
  })

  it('calls onToggle(name, true) when an unconfigured source is switched on', async () => {
    const onToggle = vi.fn()
    const user = userEvent.setup()
    render(
      <MediaSourceRow
        row={row({ name: 'mobyGames', in_chain: false })}
        onConfigure={noop}
        onDownloadPack={noop}
        onToggle={onToggle}
      />,
    )
    await user.click(screen.getByRole('switch', { name: /mobyGames/i }))
    expect(onToggle).toHaveBeenCalledWith('mobyGames', true)
  })

  it('locks the toggle on (checked + disabled) for the always-on baseline source', () => {
    render(
      <MediaSourceRow
        row={row({ name: 'libretro', in_chain: true })}
        onConfigure={noop}
        onDownloadPack={noop}
        onToggle={noop}
        locked
      />,
    )
    const toggle = screen.getByRole('switch', { name: /libretro/i })
    expect(toggle).toBeChecked()
    expect(toggle).toBeDisabled()
  })
})
