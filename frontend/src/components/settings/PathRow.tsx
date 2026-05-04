import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { FsBrowser } from '@/components/settings/FsBrowser'
import { strings } from '@/strings'

interface PathRowProps {
  id: string
  label: string
  value: string
  mode?: 'directory' | 'file'
  onChange: (next: string) => void
}

// FP12 § H — single Label + Input + Browse cell. The Input patches on blur
// (avoids per-keystroke noise); the Browse button opens an <FsBrowser>
// scoped to this row so multiple PathRows don't share a modal. The local
// draft seeds from `value` on mount; out-of-band resets (e.g. snapshot
// restore while the tab is open) won't reflect until the input is blurred.
// Parents that need a "reset draft on cancel" hook bump a `key` prop to
// re-mount this component (FP13 § B2 pattern, used by the DAT swap row).
export function PathRow({
  id,
  label,
  value,
  mode = 'directory',
  onChange,
}: PathRowProps) {
  const [draft, setDraft] = useState(value)
  const [browseOpen, setBrowseOpen] = useState(false)
  return (
    <div className="flex flex-col gap-1">
      <Label htmlFor={id}>{label}</Label>
      <div className="flex items-center gap-2">
        <Input
          id={id}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={() => {
            if (draft !== value) onChange(draft)
          }}
        />
        <Button
          variant="outline"
          onClick={() => setBrowseOpen(true)}
          aria-label={strings.settings.fsBrowseAriaLabel(label)}
        >
          {strings.settings.fsBrowserBrowse}
        </Button>
      </div>
      {browseOpen && (
        <FsBrowser
          open
          onOpenChange={setBrowseOpen}
          onPick={(picked) => {
            setDraft(picked)
            onChange(picked)
          }}
          mode={mode}
          initialPath={value || undefined}
        />
      )}
    </div>
  )
}
