import { defineConfig, devices } from '@playwright/test'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const projectRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '..',
)
const fixtureConfig = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  'e2e/fixtures/config.yaml',
)

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [['html', { open: 'never' }]],
  use: {
    baseURL: 'http://127.0.0.1:4173',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: [
    {
      // FP11 § I3: backend MUST NOT reuse a stray dev server — a
      // dev `mame-curator serve` running against the user's real
      // config.yaml would silently win, and the suite would assert
      // against the wrong dataset. Always spawn a fresh process
      // pointing at the fixture config.
      command: `uv run mame-curator serve --config ${fixtureConfig}`,
      cwd: projectRoot,
      port: 8080,
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      // Preview is reusable — it's deterministic from `frontend/dist/`,
      // not data-bound.
      command: 'npm run preview -- --port 4173 --host 127.0.0.1',
      port: 4173,
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
  ],
})
