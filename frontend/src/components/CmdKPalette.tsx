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
  const grouped: Record<CmdKSection, CmdKItem[]> = {
    games: [],
    settings: [],
    actions: [],
    help: [],
  }
  for (const item of items) grouped[item.section].push(item)

  const handleSelect = (value: string) => {
    const picked = items.find((i) => i.value === value)
    if (!picked) return
    onSelect(value, picked)
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
                  value={item.value}
                  keywords={[item.label]}
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
