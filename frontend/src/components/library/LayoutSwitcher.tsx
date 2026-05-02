import { Layout, LayoutGrid, Rows, ListIcon } from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'
import { strings } from '@/strings'
import type { LayoutName } from '@/api/types'

interface LayoutSwitcherProps {
  value: LayoutName
  onChange: (layout: LayoutName) => void
}

const LAYOUT_ORDER: LayoutName[] = ['masonry', 'list', 'covers', 'grouped']

const LAYOUT_ICONS: Record<LayoutName, typeof Layout> = {
  masonry: LayoutGrid,
  list: ListIcon,
  covers: Layout,
  grouped: Rows,
}

export function LayoutSwitcher({ value, onChange }: LayoutSwitcherProps) {
  const Icon = LAYOUT_ICONS[value]
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm">
          <Icon className="mr-2 h-4 w-4" aria-hidden="true" />
          {strings.layouts[value]}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuRadioGroup
          value={value}
          onValueChange={(v) => onChange(v as LayoutName)}
        >
          {LAYOUT_ORDER.map((layout) => (
            <DropdownMenuRadioItem key={layout} value={layout}>
              {strings.layouts[layout]}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
