import { test, expect } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

/**
 * README screenshot capture pass.
 *
 * Each "test" navigates to a target page, waits for content to settle,
 * and writes a full-viewport PNG to docs/screenshots/. The captures
 * intentionally use the real config.yaml in the project root so the
 * hero shot shows real games and real cover art.
 *
 * These aren't regression tests — failures here mean the page changed,
 * not that something's broken. Re-run on demand:
 *
 *   cd frontend
 *   npx playwright test --config screenshots/playwright.config.ts
 */
const repoRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '../..',
)
const out = (name: string) =>
  path.join(repoRoot, 'docs', 'screenshots', `${name}.png`)

test('library page (hero shot)', async ({ page }) => {
  await page.goto('/')
  // Wait for at least one game card to render.
  await expect(
    page.getByRole('button', { name: /add .+ to cart/i }).first(),
  ).toBeVisible({ timeout: 30_000 })
  // Give cover-art lazy-fetch a beat to settle so tiles aren't blank.
  await page.waitForTimeout(3_000)
  await page.screenshot({ path: out('library'), fullPage: false })
})

test('alternatives drawer (parent/clone picker)', async ({ page }) => {
  await page.goto('/')
  await expect(
    page.getByRole('button', { name: /add .+ to cart/i }).first(),
  ).toBeVisible({ timeout: 30_000 })
  await page.waitForTimeout(2_000)
  // GameCard renders as <div role="button" aria-labelledby="...">; clicking
  // it dispatches onOpen which opens the AlternativesDrawer for that game.
  const firstCard = page.locator('[role="button"][aria-labelledby]').first()
  await firstCard.click()
  await page.waitForTimeout(2_000)
  await page.screenshot({ path: out('alternatives-drawer'), fullPage: false })
})

// `settings — paths tab` capture intentionally omitted — the Paths
// inputs render the user's real /mnt/... mount paths, which we don't
// want as the README's first impression. Add it back behind a redaction
// step if it's wanted later.

test('settings — filters tab', async ({ page }) => {
  await page.goto('/settings')
  await expect(page.getByRole('tab', { name: /filters/i })).toBeVisible({
    timeout: 15_000,
  })
  await page.getByRole('tab', { name: /filters/i }).click()
  // Tab content swap is animated; wait a beat so the panel is fully rendered.
  await page.waitForTimeout(800)
  await page.screenshot({ path: out('settings-filters'), fullPage: false })
})

test('sessions panel', async ({ page }) => {
  await page.goto('/sessions')
  await expect(page.getByRole('heading', { name: /sessions/i })).toBeVisible({
    timeout: 15_000,
  })
  await page.waitForTimeout(500)
  await page.screenshot({ path: out('sessions'), fullPage: false })
})
