/**
 * Shared fixtures for the SettingsPage test files (DS05 Cluster A).
 *
 * Leading-underscore filename = not a test file. Vitest discovery
 * skips this module; `SettingsPage.test.tsx`,
 * `SettingsPage_render.test.tsx`, and
 * `SettingsPage_destructive_confirm.test.tsx` all import the
 * `render` wrapper + `config` AppConfig literal from here.
 */
import type { ReactElement } from 'react'
import { render as rtlRender } from '@testing-library/react'
import type { RenderOptions } from '@testing-library/react'
import { MemoryRouter } from 'react-router'

import type { AppConfigResponse } from '@/api/types'

// DS02 D1 — SettingsPage now calls `useSearchParams()` and therefore
// must render inside a Router. Wrap `@testing-library/react`'s render
// so every existing test (which expects a bare `render(<SettingsPage
// …/>)` to work) keeps working without per-site edits.
export function render(
  ui: ReactElement,
  options?: RenderOptions & { initialPath?: string },
) {
  const { initialPath = '/settings', ...rtlOptions } = options ?? {}
  return rtlRender(<MemoryRouter initialEntries={[initialPath]}>{ui}</MemoryRouter>, rtlOptions)
}

export const config: AppConfigResponse = {
  paths: {
    source_roms: '/mnt/roms',
    source_dat: '/mnt/dat.xml',
    dest_roms: '/mnt/dest',
    retroarch_playlist: '/mnt/mame.lpl',
    catver: null,
    languages: null,
    bestgames: null,
    mature: null,
    series: null,
    listxml: null,
    retroarch: null,
    retroarch_core: null,
  },
  server: { host: '127.0.0.1', port: 8080, open_browser_on_start: true },
  filters: {
    drop_bios_devices_mechanical: true,
    drop_categories: [],
    drop_genres: [],
    drop_publishers: [],
    drop_developers: [],
    drop_year_before: null,
    drop_year_after: null,
    drop_japanese_only_text: true,
    drop_preliminary_emulation: true,
    drop_chd_required: true,
    drop_mature: true,
    region_priority: ['World'],
    preferred_genres: [],
    preferred_publishers: [],
    preferred_developers: [],
    prefer_parent_over_clone: true,
    prefer_good_driver: true,
  },
  media: {
    fetch_videos: false,
    cache_dir: './data/media-cache',
    arcadedb_rate_limit_per_min: 30,
    mobygames_rate_limit_per_min: 5,
    sources: ['libretro', 'progettoSnaps', 'arcadeDB', 'wikipediaImage', 'mobyGames'],
  },
  ui: {
    theme: 'dark',
    layout: 'masonry',
    default_sort: 'name',
    show_alternatives_indicator: true,
    cards_per_row_hint: 'auto',
    cart_clear_on_copy: 'on_success',
  },
  updates: { channel: 'stable', check_on_startup: true, ini_check_on_startup: true },
  fs: { granted_roots: [] },
  restart_required: false,
}
