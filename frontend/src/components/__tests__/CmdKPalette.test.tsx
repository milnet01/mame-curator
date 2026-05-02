import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { CmdKPalette, type CmdKItem } from '../CmdKPalette'

const items: CmdKItem[] = [
  { id: 'g1', section: 'games', label: 'Pac-Man', value: 'pacman' },
  { id: 'g2', section: 'games', label: 'Galaga', value: 'galaga' },
  { id: 's1', section: 'settings', label: 'Theme', value: 'settings.theme' },
  { id: 'a1', section: 'actions', label: 'Run dry-run', value: 'action.dryrun' },
  { id: 'h1', section: 'help', label: 'Getting started', value: 'help.getting-started' },
]

describe('CmdKPalette', () => {
  it('lists every section when nothing is typed', () => {
    render(
      <CmdKPalette open onOpenChange={() => {}} items={items} onSelect={() => {}} />,
    )
    expect(screen.getByText('Pac-Man')).toBeInTheDocument()
    expect(screen.getByText('Theme')).toBeInTheDocument()
    expect(screen.getByText('Run dry-run')).toBeInTheDocument()
    expect(screen.getByText('Getting started')).toBeInTheDocument()
  })

  it('filters across sections by typed prefix', async () => {
    render(
      <CmdKPalette open onOpenChange={() => {}} items={items} onSelect={() => {}} />,
    )
    await userEvent.type(screen.getByRole('combobox'), 'pac')
    expect(screen.getByText('Pac-Man')).toBeInTheDocument()
    expect(screen.queryByText('Galaga')).toBeNull()
    expect(screen.queryByText('Theme')).toBeNull()
  })

  it('calls onSelect with the picked item value', async () => {
    const onSelect = vi.fn()
    render(
      <CmdKPalette open onOpenChange={() => {}} items={items} onSelect={onSelect} />,
    )
    await userEvent.click(screen.getByText('Galaga'))
    expect(onSelect).toHaveBeenCalledWith('galaga', expect.objectContaining({ id: 'g2' }))
  })
})
