import { useState } from 'react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { strings } from '@/strings'

interface DownloadPackModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}


/**
 * P10 chunk 10 — the progettoSnaps snapshot pack is ~500 MB, so instead of a
 * backend download endpoint this shows the `mame-curator refresh-snaps` command
 * with a copy button (a terminal hint). After running it the user reopens the
 * tab and the readiness refetch flips progettoSnaps to Active.
 */
export function DownloadPackModal({ open, onOpenChange }: DownloadPackModalProps) {
  const [copied, setCopied] = useState(false)

  const onCopy = () => {
    // navigator.clipboard is undefined in non-secure (plain-HTTP LAN) contexts,
    // and writeText can reject on a permissions denial — only flip to "Copied!"
    // on a real success so the button never lies. (FP32 H2)
    if (!navigator.clipboard) return
    Promise.resolve(navigator.clipboard.writeText(strings.settings.mediaPackModal.command))
      .then(() => setCopied(true))
      .catch(() => {
        /* copy failed (permissions / non-secure) — leave the button un-flipped */
      })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{strings.settings.mediaPackModal.title}</DialogTitle>
          <DialogDescription>{strings.settings.mediaPackModal.body}</DialogDescription>
        </DialogHeader>
        <div className="flex items-center gap-2">
          <code className="min-w-0 flex-1 truncate rounded bg-muted px-2 py-1 text-sm">
            {strings.settings.mediaPackModal.command}
          </code>
          <Button variant="outline" size="sm" onClick={onCopy}>
            {copied ? strings.settings.mediaPackModal.copied : strings.settings.mediaPackModal.copyButton}
          </Button>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            {strings.settings.mediaPackModal.close}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
