import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
    },
  },
  // shadcn/ui primitives are vendored verbatim from `npx shadcn add` and
  // ship a non-component co-export (a `cva()` variants helper) that trips
  // `react-refresh/only-export-components`. Refactoring upstream's output
  // diverges from the registry and breaks the next `shadcn add`'s diff
  // (audit-allowlist.md § allowlist-003).
  {
    files: ['src/components/ui/**/*.{ts,tsx}'],
    rules: {
      'react-refresh/only-export-components': 'off',
    },
  },
  // `@tanstack/react-virtual`'s `useVirtualizer()` returns non-stable
  // accessor functions by design — the React Compiler eslint plugin
  // emits an "incompatible library" warning every render. Library-by-
  // design, not a project defect (audit-allowlist.md § allowlist-002).
  {
    files: ['src/components/library/LibraryGrid.tsx'],
    rules: {
      'react-hooks/incompatible-library': 'off',
    },
  },
])
