import type { ThemeName } from '@/api/types'

/**
 * Mutates `<html data-theme>` so the matching `@theme` block in
 * `index.css` cascades to every shadcn primitive.
 *
 * Lives in its own module rather than alongside `ThemeSwitcher` so
 * importing the helper doesn't trip eslint's
 * `react-refresh/only-export-components` rule (component files must
 * only export components for Fast Refresh to work). Single writer:
 * the only caller is `ThemeProvider`, which mirrors `useConfig`'s
 * `ui.theme` value into the DOM. `ThemeSwitcher`'s click handler
 * dispatches `onChange` and lets the provider apply the change so
 * the DOM mutation happens once, not twice.
 */
export function applyTheme(theme: ThemeName) {
  document.documentElement.setAttribute('data-theme', theme)
}
