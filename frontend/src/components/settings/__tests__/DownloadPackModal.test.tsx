import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { DownloadPackModal } from '../DownloadPackModal'

describe('DownloadPackModal', () => {
  it('copies the refresh-snaps command to the clipboard (no network)', () => {
    const writeText = vi.fn()
    // Define before render so userEvent's clipboard stub doesn't shadow it;
    // fireEvent (not userEvent) keeps this mock in force.
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    render(<DownloadPackModal open onOpenChange={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: /copy command/i }))
    expect(writeText).toHaveBeenCalledWith('mame-curator refresh-snaps')
  })
})
