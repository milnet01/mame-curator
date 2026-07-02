import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { DownloadPackModal } from '../DownloadPackModal'

describe('DownloadPackModal', () => {
  it('copies the refresh-snaps command to the clipboard (no network)', () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    // Define before render so userEvent's clipboard stub doesn't shadow it;
    // fireEvent (not userEvent) keeps this mock in force.
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    render(<DownloadPackModal open onOpenChange={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: /copy command/i }))
    expect(writeText).toHaveBeenCalledWith('mame-curator refresh-snaps')
  })

  it('FP32 H2: does not throw when navigator.clipboard is undefined (non-secure LAN)', () => {
    Object.defineProperty(navigator, 'clipboard', { value: undefined, configurable: true })
    render(<DownloadPackModal open onOpenChange={() => {}} />)
    // Clicking must not throw; the button must not falsely flip to "Copied!".
    fireEvent.click(screen.getByRole('button', { name: /copy command/i }))
    expect(screen.getByRole('button', { name: /copy command/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /copied/i })).toBeNull()
  })

  it('FP32 H2: does not claim "Copied!" when writeText rejects', async () => {
    const writeText = vi.fn().mockRejectedValue(new Error('permission denied'))
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    render(<DownloadPackModal open onOpenChange={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: /copy command/i }))
    await waitFor(() => expect(writeText).toHaveBeenCalled())
    // A rejected writeText must leave the button un-flipped — no false success.
    expect(screen.queryByRole('button', { name: /copied/i })).toBeNull()
    expect(screen.getByRole('button', { name: /copy command/i })).toBeInTheDocument()
  })
})
