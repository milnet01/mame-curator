import { defineConfig, devices } from '@playwright/test'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

/**
 * Playwright config for README screenshots — separate from the
 * regression-test config (frontend/playwright.config.ts) so the CI suite
 * keeps using the deterministic 6-machine fixture DAT while screenshots
 * use the real config + real DAT at the repo root.
 *
 * Run:
 *   cd frontend
 *   npx playwright test --config screenshots/playwright.config.ts
 *
 * Output: docs/screenshots/*.png (committed to the repo).
 */
const projectRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '../..',
)
const realConfig = path.join(projectRoot, 'config.yaml')

export default defineConfig({
  testDir: '.',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:4173',
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: [
    {
      // `--no-open-browser` because this one runs against the REAL config,
      // which has `open_browser_on_start: true` — without it every
      // screenshot run opens a browser tab, and Playwright then stops the
      // server it points at, so the tab lands on a dead port. The flag is
      // one-way suppression (cli/spec.md § Browser), so it cannot turn an
      // open *on* against a config saying false.
      command: `uv run mame-curator serve --config ${realConfig} --no-open-browser`,
      cwd: projectRoot,
      port: 8080,
      reuseExistingServer: true,
      timeout: 60_000,
    },
    {
      command: 'npm run preview -- --port 4173 --host 127.0.0.1',
      port: 4173,
      reuseExistingServer: true,
      timeout: 30_000,
    },
  ],
})
