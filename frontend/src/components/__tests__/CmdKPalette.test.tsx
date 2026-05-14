import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { CmdKPalette, type CmdKItem } from '../CmdKPalette'

// FP27 A5: dropped 'games' and 'settings' fixture items (the only
// producers in the codebase). The palette now hosts 'actions' + 'help'
// only; fixtures here mirror that.
const items: CmdKItem[] = [
  { id: 'a1', section: 'actions', label: 'Run dry-run', value: 'action.dryrun' },
  { id: 'a2', section: 'actions', label: 'Copy selected', value: 'action.copy' },
  { id: 'h1', section: 'help', label: 'Getting started', value: 'help.getting-started' },
  { id: 'h2', section: 'help', label: 'Keyboard shortcuts', value: 'help.shortcuts' },
]

describe('CmdKPalette', () => {
  it('lists every section when nothing is typed', () => {
    render(
      <CmdKPalette open onOpenChange={() => {}} items={items} onSelect={() => {}} />,
    )
    expect(screen.getByText('Run dry-run')).toBeInTheDocument()
    expect(screen.getByText('Copy selected')).toBeInTheDocument()
    expect(screen.getByText('Getting started')).toBeInTheDocument()
    expect(screen.getByText('Keyboard shortcuts')).toBeInTheDocument()
  })

  it('filters across sections by typed prefix', async () => {
    render(
      <CmdKPalette open onOpenChange={() => {}} items={items} onSelect={() => {}} />,
    )
    await userEvent.type(screen.getByRole('combobox'), 'dry')
    expect(screen.getByText('Run dry-run')).toBeInTheDocument()
    expect(screen.queryByText('Copy selected')).toBeNull()
    expect(screen.queryByText('Getting started')).toBeNull()
  })

  it('calls onSelect with the picked item value', async () => {
    const onSelect = vi.fn()
    render(
      <CmdKPalette open onOpenChange={() => {}} items={items} onSelect={onSelect} />,
    )
    await userEvent.click(screen.getByText('Copy selected'))
    expect(onSelect).toHaveBeenCalledWith('action.copy', expect.objectContaining({ id: 'a2' }))
  })

  it('matches when the user types a hint (FP11 § B7)', async () => {
    const itemsWithHint: CmdKItem[] = [
      ...items,
      {
        id: 'a3',
        section: 'actions',
        label: 'Refresh INIs',
        value: 'action.refresh-inis',
        hint: 'updates catver, languages, bestgames',
      },
    ]
    render(
      <CmdKPalette
        open
        onOpenChange={() => {}}
        items={itemsWithHint}
        onSelect={() => {}}
      />,
    )
    await userEvent.type(screen.getByRole('combobox'), 'catver')
    // The hint text was added to keywords; cmdk should match.
    expect(screen.getByText('Refresh INIs')).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// FP27 A5 — CmdK 'games' and 'settings' sections removed
//
// `SECTION_ORDER` at CmdKPalette.tsx:30 declares four sections
// ['games', 'settings', 'actions', 'help'], but zero production code
// produces items with `section: 'games'` or `section: 'settings'` — the
// only producers are these test fixtures (and the strings.cmdK.sections
// catalogue entry).
//
// A5 removes both from four lockstep call-sites: the type union, the
// SECTION_ORDER array, the `grouped` initializer, and the
// `strings.cmdK.sections.{games,settings}` entries in strings.ts.
//
// Pre-fix: SECTION_ORDER contains both → fails. Post-fix: only
// {'actions', 'help'} remain.
// ---------------------------------------------------------------------------

describe('FP27 A5 — CmdK games/settings sections removed', () => {
  it("SECTION_ORDER excludes 'games' and 'settings'", async () => {
    const mod = await import('../CmdKPalette')
    const sectionOrder = (mod as unknown as { SECTION_ORDER?: readonly string[] })
      .SECTION_ORDER
    if (!sectionOrder) {
      // SECTION_ORDER not exported today; lift the export as part of A5
      // (one-line change). Fail clearly until then.
      throw new Error(
        'SECTION_ORDER must be exported from CmdKPalette.tsx so this test ' +
          "can assert it; see `docs/specs/FP27.md` § A5.",
      )
    }
    expect(sectionOrder).not.toContain('games')
    expect(sectionOrder).not.toContain('settings')
    expect(new Set(sectionOrder)).toEqual(new Set(['actions', 'help']))
  })

  it('strings.cmdK.sections has no games/settings keys', async () => {
    const { strings } = await import('@/strings')
    const sections = strings.cmdK.sections as Record<string, string>
    expect(sections).not.toHaveProperty('games')
    expect(sections).not.toHaveProperty('settings')
  })
})
