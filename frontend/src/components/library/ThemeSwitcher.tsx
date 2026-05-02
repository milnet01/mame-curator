import { Palette } from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'
import type { ThemeName } from '@/api/types'

interface ThemeSwitcherProps {
  value: ThemeName
  onChange: (theme: ThemeName) => void
}

const THEME_LABELS: Record<ThemeName, string> = {
  dark: 'Dark',
  light: 'Light',
  double_dragon: 'Double Dragon',
  pacman: 'Pac-Man',
  sf2: 'SF2',
  neogeo: 'Neo Geo',
}

const THEME_ORDER: ThemeName[] = [
  'dark',
  'light',
  'double_dragon',
  'pacman',
  'sf2',
  'neogeo',
]

export function applyTheme(theme: ThemeName) {
  document.documentElement.setAttribute('data-theme', theme)
}

export function ThemeSwitcher({ value, onChange }: ThemeSwitcherProps) {
  const handleChange = (next: string) => {
    const theme = next as ThemeName
    applyTheme(theme)
    onChange(theme)
  }
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm">
          <Palette className="mr-2 h-4 w-4" aria-hidden="true" />
          {THEME_LABELS[value]}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuRadioGroup value={value} onValueChange={handleChange}>
          {THEME_ORDER.map((theme) => (
            <DropdownMenuRadioItem key={theme} value={theme}>
              {THEME_LABELS[theme]}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
