/**
 * FP27 A6a — `Esc` closes drawer / dialog overlays (Radix-delivered).
 *
 * `docs/design.md` § keyboard shortcuts promises:
 *     - `Esc` — close drawer / dialog (provided ambiently by Radix …)
 *
 * No `useKeyboard` binding delivers it; Radix's `Dialog` and `AlertDialog`
 * primitives intercept `Escape` themselves, and the drawer (`Sheet`) is a
 * Radix `Dialog` underneath. This file is the only lock on that promise.
 *
 * Restored by mame-curator-1062. DS04 T3.9 deleted it as third-party
 * coverage, but a Radix upgrade that dropped the ambient handler would
 * then break the promise with nothing failing. If this ever fails,
 * FP27 A6a escalates to A6c: wire `Esc` ourselves or drop the promise.
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
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
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
    expect(
      screen.getByRole('alertdialog', { name: 'Delete 3 files' }),
    ).toBeInTheDocument()
    await userEvent.keyboard('{Escape}')
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('plain Dialog closes when Esc is dispatched', async () => {
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

  it('drawer (Sheet) closes when Esc is dispatched', async () => {
    const onOpenChange = vi.fn()
    render(
      <Sheet open onOpenChange={onOpenChange}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>Drawer under test</SheetTitle>
            <SheetDescription>Game details</SheetDescription>
          </SheetHeader>
        </SheetContent>
      </Sheet>,
    )
    expect(
      screen.getByRole('dialog', { name: 'Drawer under test' }),
    ).toBeInTheDocument()
    await userEvent.keyboard('{Escape}')
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })
})
