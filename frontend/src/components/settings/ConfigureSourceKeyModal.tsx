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
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ApiError } from '@/api/client'
import { useSaveSourceSecret } from '@/hooks/useMediaSources'
import { strings } from '@/strings'

interface ConfigureSourceKeyModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  sourceName: string
}


/**
 * P10 chunk 10 — paste a value-paste source's API key (currently mobyGames).
 * On a 204 the modal closes and the readiness query is invalidated (the dot
 * flips green). On a 422 the modal stays open with an inline error.
 */
export function ConfigureSourceKeyModal({
  open,
  onOpenChange,
  sourceName,
}: ConfigureSourceKeyModalProps) {
  const [secret, setSecret] = useState('')
  const save = useSaveSourceSecret()

  // Defensive clear: wipe the typed key (and any stale error) on close so a
  // reopen starts blank instead of relying on unmount to drop the state.
  const handleOpenChange = (next: boolean) => {
    if (!next) {
      setSecret('')
      save.reset()
    }
    onOpenChange(next)
  }

  const onSave = () => {
    save.mutate(
      { name: sourceName, secret },
      {
        onSuccess: () => {
          setSecret('')
          onOpenChange(false)
        },
      },
    )
  }

  // Surface the server's ApiError detail (e.g. unknown-source vs bad-key)
  // rather than a fixed generic string the user can't act on.
  const errorText =
    save.error instanceof ApiError ? save.error.detail : strings.settings.mediaKeyModal.error

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{strings.settings.mediaKeyModal.title}</DialogTitle>
          <DialogDescription>{strings.settings.mediaKeyModal.body}</DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-1">
          <Label htmlFor="media-source-key">{strings.settings.mediaKeyModal.inputLabel}</Label>
          <Input
            id="media-source-key"
            type="password"
            value={secret}
            onChange={(e) => setSecret(e.target.value)}
          />
          {save.isError && (
            <p role="alert" className="text-xs text-destructive">
              {errorText}
            </p>
          )}
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => handleOpenChange(false)}>
            {strings.settings.mediaKeyModal.cancel}
          </Button>
          <Button onClick={onSave} disabled={secret.length === 0 || save.isPending}>
            {strings.settings.mediaKeyModal.save}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
