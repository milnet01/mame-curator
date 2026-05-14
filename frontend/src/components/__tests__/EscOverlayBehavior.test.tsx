/**
 * FP27 A6a — `Esc` closes drawer / dialog overlays (Radix-delivered).
 *
 * The design spec at
 * `docs/superpowers/specs/2026-04-27-mame-curator-design.md:602`
 * advertises:
 *     - `Esc` — close drawer / dialog
 *
 * `frontend/src/App.tsx:316-318` registers exactly one `useKeyboard`
 * binding (`combo: 'k'` with `meta:true`); there is no `Esc` binding.
 * The behavior is delivered ambiently by Radix's `<AlertDialog>` and
 * `<Dialog>` primitives, which intercept `Escape` natively.
 *
 * A6a's fix is doc-truthing: keep the design-spec line, append a credit
 * "(provided ambiently by Radix `<Dialog>` / `<AlertDialog>` primitives)".
 * No new wiring.
 *
 * This test pins the empirical behavior. It should PASS pre-fix
 * (because Radix already delivers Esc-close) and continue to pass
 * post-fix. If it ever FAILS, that's the trigger to escalate A6a to
 * A6c (remove the bullet from the design spec entirely).
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { ConfirmationDialog } from '../ConfirmationDialog'

afterEach(() => {
  cleanup()
})

describe('FP27 A6a — Radix overlays close on Esc', () => {
  it('AlertDialog (via ConfirmationDialog) closes when Esc is dispatched', async () => {
    const onOpenChange = vi.fn()
    render(
      <ConfirmationDialog
        open
        onOpenChange={onOpenChange}
        title="Delete 3 files"
        description="Permanently delete 3 files from drive"
        actionLabel="Delete 3 files from drive"
        onConfirm={() => {}}
      />,
    )

    // The dialog content is rendered (Radix renders it into a portal).
    expect(
      screen.getByRole('alertdialog', { name: 'Delete 3 files' }),
    ).toBeInTheDocument()

    // Dispatch Escape. Radix's <AlertDialogContent /> wires
    // `onEscapeKeyDown` → close, so `onOpenChange(false)` must fire.
    await userEvent.keyboard('{Escape}')

    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('plain Dialog closes when Esc is dispatched', async () => {
    // The design-spec line credits BOTH primitives (Dialog +
    // AlertDialog). Cover plain Dialog too so a future Radix upgrade
    // that regresses one primitive without the other gets caught.
    const onOpenChange = vi.fn()
    render(
      <Dialog open onOpenChange={onOpenChange}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Plain dialog under test</DialogTitle>
          </DialogHeader>
        </DialogContent>
      </Dialog>,
    )
    expect(
      screen.getByRole('dialog', { name: 'Plain dialog under test' }),
    ).toBeInTheDocument()
    await userEvent.keyboard('{Escape}')
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })
})
