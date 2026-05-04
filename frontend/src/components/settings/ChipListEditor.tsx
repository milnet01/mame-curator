import { useState, type ClipboardEvent, type KeyboardEvent } from 'react'

import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

export interface ChipListEditorProps {
  /** Accessible name for the chip list (e.g. "Drop genres"). */
  ariaLabel: string
  /** Current chip values; rendered in order. */
  value: string[]
  /** Called with the next list whenever it changes. */
  onChange: (next: string[]) => void
  /** Placeholder for the trailing add input. */
  addPlaceholder: string
  /** Optional id for the trailing input (lets `<Label htmlFor>` target it). */
  inputId?: string
}

function addItems(current: string[], incoming: string[]): string[] | null {
  const seen = new Set(current)
  const additions: string[] = []
  for (const raw of incoming) {
    const trimmed = raw.trim()
    if (!trimmed || seen.has(trimmed)) continue
    seen.add(trimmed)
    additions.push(trimmed)
  }
  return additions.length === 0 ? null : [...current, ...additions]
}

export function ChipListEditor({
  ariaLabel,
  value,
  onChange,
  addPlaceholder,
  inputId,
}: ChipListEditorProps) {
  const [draft, setDraft] = useState('')

  const commit = (incoming: string[]) => {
    const next = addItems(value, incoming)
    if (next) onChange(next)
  }

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      event.preventDefault()
      commit([draft])
      setDraft('')
      return
    }
    if (event.key === 'Backspace' && draft === '' && value.length > 0) {
      event.preventDefault()
      onChange(value.slice(0, -1))
    }
  }

  const onPaste = (event: ClipboardEvent<HTMLInputElement>) => {
    const text = event.clipboardData.getData('text')
    if (!text.includes(',')) return
    event.preventDefault()
    commit(text.split(','))
    setDraft('')
  }

  const remove = (item: string) => {
    onChange(value.filter((v) => v !== item))
  }

  return (
    <div className="flex flex-col gap-2">
      <ul
        role="list"
        aria-label={ariaLabel}
        className={cn(
          'flex flex-wrap gap-1',
          value.length === 0 && 'sr-only',
        )}
      >
        {value.map((item) => (
          <li key={item}>
            <button
              type="button"
              // FP13 § D1: include the list label in the chip's accessible
              // name so screen readers in flattened-browse mode (where the
              // <ul aria-label> wrapper isn't read alongside each item)
              // still know which chip list this chip belongs to.
              aria-label={`Remove ${item} from ${ariaLabel}`}
              onClick={() => remove(item)}
              className="inline-flex items-center gap-1 rounded-full border border-input bg-muted px-2 py-0.5 text-xs hover:bg-muted/70 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <span>{item}</span>
              <span aria-hidden="true">×</span>
            </button>
          </li>
        ))}
      </ul>
      <Input
        id={inputId}
        type="text"
        value={draft}
        placeholder={addPlaceholder}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={onKeyDown}
        onPaste={onPaste}
      />
    </div>
  )
}
