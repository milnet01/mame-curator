import { expect, test } from '@playwright/test'

/**
 * Smoke-coverage E2E: validates that the production bundle boots, the
 * shell renders, react-router navigates, and the static mount + API
 * mount cohabit correctly.
 *
 * The full spec scenario (search → alternatives drawer → override →
 * dry-run → copy → pause/resume → conflict resolve → theme + layout
 * switch end-to-end) needs a richer fixture tree (real ROM `.zip`
 * payloads + a CI-friendly conflict-prone playlist) and lands as a
 * `FP##` follow-up after P06 closes.
 */

test('production shell loads and the left rail navigates between routes', async ({ page }) => {
  await page.goto('/')

  // Library nav link is rendered.
  await expect(page.getByRole('link', { name: 'Library', exact: true })).toBeVisible()

  // App heading lives in the left rail (use the rail h1 to avoid the
  // CmdKPalette dialog title shadow).
  await expect(page.locator('aside h1')).toHaveText('MAME Curator')

  // Navigate via the rail.
  await page.getByRole('link', { name: 'Sessions' }).click()
  await expect(page).toHaveURL(/\/sessions$/)

  await page.getByRole('link', { name: 'Stats' }).click()
  await expect(page).toHaveURL(/\/stats$/)

  await page.getByRole('link', { name: 'Settings' }).click()
  await expect(page).toHaveURL(/\/settings$/)

  // Back to Library. The link is in the rail; the click target text "Library"
  // also matches the heading so use the link role explicitly.
  await page.getByRole('link', { name: 'Library', exact: true }).click()
})
