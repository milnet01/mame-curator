import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

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
      <MediaSourceRow row={row()} onConfigure={noop} onDownloadPack={noop} />,
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
      />,
    )
    expect(screen.queryByRole('button', { name: /configure/i })).toBeNull()
  })
})
