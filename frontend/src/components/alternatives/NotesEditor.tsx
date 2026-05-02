import { useState } from 'react'
import { Label } from '@/components/ui/label'
import { strings } from '@/strings'

interface NotesEditorProps {
  initial: string
  onSave: (notes: string) => Promise<void>
}

type SaveState = 'idle' | 'saving' | 'saved' | 'error'

/**
 * Notes editor for the alternatives drawer.
 *
 * **Mount-on-game-change contract.** When the parent navigates to a
 * different game, it MUST pass a stable `key` (typically the game's
 * short_name) so React re-mounts the editor with fresh state. We do
 * NOT do an in-render `initial !== lastInitial` comparison — that
 * pattern requires reading refs during render, which the React 19
 * compiler eslint rules forbid. The unmount-and-remount story is
 * cheaper than the manual sync was, plus it eliminates the stale-
 * "Saved"-flash-on-game-switch race (FP11 § D2).
 *
 * **Save lifecycle.** Blur with an unchanged draft is a no-op (and
 * preserves the prior save-state badge). Blur with a changed draft
 * fires `onSave`; on success the draft becomes the new lastSaved
 * baseline; on failure the badge flips to `error` (role="alert" so
 * AT users hear the failure) and stays until the next successful
 * save or unmount. Each save attempt resets to `saving` first, so
 * the user can't see a stale `error` while a fresh attempt is in
 * flight.
 */
export function NotesEditor({ initial, onSave }: NotesEditorProps) {
  const [draft, setDraft] = useState(initial)
  const [lastSaved, setLastSaved] = useState(initial)
  const [saveState, setSaveState] = useState<SaveState>('idle')

  const handleBlur = async () => {
    if (draft === lastSaved) return
    setSaveState('saving')
    try {
      await onSave(draft)
      setLastSaved(draft)
      setSaveState('saved')
    } catch {
      setSaveState('error')
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <Label htmlFor="notes-editor">{strings.alternatives.notesLabel}</Label>
        <span
          className="text-xs text-muted-foreground"
          role={saveState === 'error' ? 'alert' : 'status'}
          aria-live={saveState === 'error' ? 'assertive' : 'polite'}
          aria-atomic="true"
        >
          {saveState === 'saving' && strings.notes.saving}
          {saveState === 'saved' && strings.notes.saved}
          {saveState === 'error' && strings.notes.saveError}
        </span>
      </div>
      <textarea
        id="notes-editor"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={handleBlur}
        placeholder={strings.alternatives.notesPlaceholder}
        rows={4}
        className="w-full rounded border bg-background p-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      />
    </div>
  )
}
