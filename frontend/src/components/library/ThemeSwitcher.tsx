import { Palette } from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'
import { strings } from '@/strings'
import type { ThemeName } from '@/api/types'

interface ThemeSwitcherProps {
  value: ThemeName
  onChange: (theme: ThemeName) => void
}

const THEME_ORDER: ThemeName[] = [
  'dark',
  'light',
  'double_dragon',
  'pacman',
  'sf2',
  'neogeo',
]

export function ThemeSwitcher({ value, onChange }: ThemeSwitcherProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm">
          <Palette className="mr-2 h-4 w-4" aria-hidden="true" />
          {strings.themes[value]}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuRadioGroup
          value={value}
          onValueChange={(next) => onChange(next as ThemeName)}
        >
          {THEME_ORDER.map((theme) => (
            <DropdownMenuRadioItem key={theme} value={theme}>
              {strings.themes[theme]}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
