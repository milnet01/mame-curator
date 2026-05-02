import { useEffect, useRef, useState } from 'react'
import { Label } from '@/components/ui/label'
import { strings } from '@/strings'

interface NotesEditorProps {
  initial: string
  onSave: (notes: string) => Promise<void>
}

type SaveState = 'idle' | 'saving' | 'saved' | 'error'

export function NotesEditor({ initial, onSave }: NotesEditorProps) {
  const [draft, setDraft] = useState(initial)
  const [saveState, setSaveState] = useState<SaveState>('idle')
  const lastSaved = useRef(initial)

  // Re-sync the draft when the parent feeds in a new initial value (e.g.
  // navigating between games while the drawer stays mounted).
  useEffect(() => {
    setDraft(initial)
    lastSaved.current = initial
  }, [initial])

  const handleBlur = async () => {
    if (draft === lastSaved.current) return
    setSaveState('saving')
    try {
      await onSave(draft)
      lastSaved.current = draft
      setSaveState('saved')
    } catch {
      setSaveState('error')
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <Label htmlFor="notes-editor">Notes</Label>
        <span className="text-xs text-muted-foreground" aria-live="polite">
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
