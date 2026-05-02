import { useEffect, type ReactNode } from 'react'
import type { ThemeName } from '@/api/types'
import { applyTheme } from '@/components/library/ThemeSwitcher'

interface ThemeProviderProps {
  theme: ThemeName
  children: ReactNode
}

/** Sets `data-theme` on `<html>` whenever the prop changes. */
export function ThemeProvider({ theme, children }: ThemeProviderProps) {
  useEffect(() => {
    applyTheme(theme)
  }, [theme])
  return <>{children}</>
}
