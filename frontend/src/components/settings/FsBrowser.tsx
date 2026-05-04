import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { ConfirmationDialog } from '@/components/ConfirmationDialog'
import {
  useFsAllowedRoots,
  useFsDriveRoots,
  useFsGrantRoot,
  useFsHome,
  useFsListing,
} from '@/hooks/useFs'
import { strings } from '@/strings'

interface FsBrowserProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onPick: (path: string) => void
  /** 'directory' (default) shows / picks dirs only; 'file' also shows files
      and clicking a file fires onPick. */
  mode?: 'directory' | 'file'
  /** Path to start at; falls back to the home directory once it loads. */
  initialPath?: string
}

export function FsBrowser({
  open,
  onOpenChange,
  onPick,
  mode = 'directory',
  initialPath,
}: FsBrowserProps) {
  const home = useFsHome()
  const driveRoots = useFsDriveRoots()
  const allowed = useFsAllowedRoots()
  const grant = useFsGrantRoot()

  // userPath holds a user-navigated path; falls back to home until they
  // pick something. Derived `path` keeps default-on-async-load drift-free
  // (project rule against setState-in-effect).
  const [userPath, setUserPath] = useState<string | null>(initialPath ?? null)
  const path = userPath ?? home.data?.path ?? null

  const listing = useFsListing(path)

  // R33 grant flow — surface a confirm dialog if `path` is outside the
  // allowlist (`fs_sandboxed` 403 from R29). On confirm we POST the path
  // and react-query auto-refetches the listing. Duck-typed `code` check
  // tolerates module-identity differences across vitest's module graph.
  const errCode =
    listing.error &&
    typeof (listing.error as unknown as { code?: unknown }).code === 'string'
      ? (listing.error as unknown as { code: string }).code
      : null
  const sandboxBlocked = errCode === 'fs_sandboxed' ? path : null

  if (!open) return null

  const goUp = () => {
    if (listing.data?.parent) setUserPath(listing.data.parent)
  }

  const handleEntryClick = (entryPath: string, isDir: boolean) => {
    if (isDir) {
      setUserPath(entryPath)
    } else if (mode === 'file') {
      onPick(entryPath)
      onOpenChange(false)
    }
  }

  const usePath = () => {
    if (path) {
      onPick(path)
      onOpenChange(false)
    }
  }

  const visibleEntries = (listing.data?.entries ?? []).filter(
    (e) => mode === 'file' || e.is_dir,
  )

  return (
    <>
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{strings.settings.fsBrowserTitle}</DialogTitle>
          <DialogDescription>
            {strings.settings.fsBrowserDescription}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-wrap items-center gap-2 text-xs">
          <Button
            size="sm"
            variant="outline"
            onClick={() => home.data && setUserPath(home.data.path)}
            disabled={!home.data}
          >
            {strings.settings.fsBrowserHome}
          </Button>
          {(allowed.data?.roots ?? []).map((r) => (
            <Button
              key={r.id}
              size="sm"
              variant="outline"
              onClick={() => setUserPath(r.path)}
            >
              {r.path}
            </Button>
          ))}
          {(driveRoots.data?.roots ?? []).map((r) => (
            <Button
              key={r}
              size="sm"
              variant="outline"
              onClick={() => setUserPath(r)}
            >
              {r}
            </Button>
          ))}
        </div>

        <div className="flex items-center gap-2 text-sm">
          <Button
            size="sm"
            variant="outline"
            onClick={goUp}
            disabled={!listing.data?.parent}
          >
            {strings.settings.fsBrowserUp}
          </Button>
          <code className="flex-1 truncate">{path ?? ''}</code>
        </div>

        {listing.isLoading && (
          <p className="text-sm text-muted-foreground">
            {strings.settings.fsBrowserLoading}
          </p>
        )}
        {listing.error && !sandboxBlocked && (
          <p role="alert" className="text-sm text-destructive">
            {strings.settings.fsBrowserListError}
          </p>
        )}
        {!listing.isLoading && !listing.error && (
          <ul className="max-h-72 overflow-auto rounded border border-muted">
            {visibleEntries.map((entry) => (
              <li key={entry.path}>
                <button
                  type="button"
                  className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-muted/40"
                  onClick={() => handleEntryClick(entry.path, entry.is_dir)}
                >
                  <span>{entry.name}</span>
                  <span className="text-xs text-muted-foreground">
                    {entry.is_dir ? strings.settings.fsBrowserDirTag : ''}
                  </span>
                </button>
              </li>
            ))}
            {visibleEntries.length === 0 && (
              <li className="px-3 py-2 text-sm text-muted-foreground">
                {strings.settings.fsBrowserEmpty}
              </li>
            )}
          </ul>
        )}

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            {strings.common.cancel}
          </Button>
          <Button
            onClick={usePath}
            disabled={!path || mode !== 'directory' || !!sandboxBlocked}
          >
            {strings.settings.fsBrowserUseDirectory}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    {sandboxBlocked && (
      <ConfirmationDialog
        open
        onOpenChange={(o) => {
          if (!o && home.data) setUserPath(home.data.path)
        }}
        title={strings.settings.fsGrantTitle}
        description={strings.settings.fsGrantConfirm(sandboxBlocked)}
        actionLabel={strings.settings.fsGrantActionLabel(sandboxBlocked)}
        onConfirm={() => grant.mutate(sandboxBlocked)}
        destructive={false}
      />
    )}
    </>
  )
}
