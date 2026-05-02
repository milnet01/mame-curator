import { useMemo } from 'react'
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { strings } from '@/strings'

export type CmdKSection = 'games' | 'settings' | 'actions' | 'help'

export interface CmdKItem {
  id: string
  section: CmdKSection
  label: string
  value: string
  /** Optional secondary text shown after the label. */
  hint?: string
}

interface CmdKPaletteProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  items: CmdKItem[]
  onSelect: (value: string, item: CmdKItem) => void
}

const SECTION_ORDER: CmdKSection[] = ['games', 'settings', 'actions', 'help']

export function CmdKPalette({
  open,
  onOpenChange,
  items,
  onSelect,
}: CmdKPaletteProps) {
  // FP11 § B7: pre-bucket once per items-prop change so the palette
  // doesn't pay an O(items × sections) cost per keystroke. Memoised
  // off `items` identity — caller is expected to keep the array
  // stable across renders.
  const grouped = useMemo(() => {
    const out: Record<CmdKSection, CmdKItem[]> = {
      games: [],
      settings: [],
      actions: [],
      help: [],
    }
    for (const item of items) out[item.section].push(item)
    return out
  }, [items])

  // cmdk's `<CommandItem value={...}>` is the field its fuzzy matcher
  // scores against — we set it to the **id** (stable, opaque) so
  // routing-shaped values (e.g. `/settings/paths`) don't leak into
  // the search match. Free-text matching is driven by `keywords`.
  const handleSelect = (id: string) => {
    const picked = items.find((i) => i.id === id)
    if (!picked) return
    onSelect(picked.value, picked)
    onOpenChange(false)
  }

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange} title={strings.app.name}>
      <CommandInput placeholder={strings.cmdK.placeholder} />
      <CommandList>
        <CommandEmpty>{strings.cmdK.emptyHint}</CommandEmpty>
        {SECTION_ORDER.map((section) =>
          grouped[section].length === 0 ? null : (
            <CommandGroup
              key={section}
              heading={strings.cmdK.sections[section]}
            >
              {grouped[section].map((item) => (
                <CommandItem
                  key={item.id}
                  value={item.id}
                  keywords={[
                    item.label,
                    ...(item.hint ? [item.hint] : []),
                    strings.cmdK.sections[item.section],
                  ]}
                  onSelect={handleSelect}
                >
                  <span>{item.label}</span>
                  {item.hint && (
                    <span className="ml-auto text-xs text-muted-foreground">
                      {item.hint}
                    </span>
                  )}
                </CommandItem>
              ))}
            </CommandGroup>
          ),
        )}
      </CommandList>
    </CommandDialog>
  )
}
