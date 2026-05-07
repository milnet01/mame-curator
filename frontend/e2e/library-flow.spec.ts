import { expect, test } from '@playwright/test'

/**
 * Smoke-coverage E2E (P06 + P15 § F12 reshape):
 *   - Production bundle boots, preview server cohabits with API.
 *   - Top-nav header renders (replaces the P06 left rail per § F12).
 *   - Primary routes (Library / Settings / Help) still navigate
 *     directly via top-nav clicks; URL paths preserved so existing
 *     bookmarks survive.
 *   - Secondary routes (Sessions / Activity / Stats) navigate via
 *     the new "More" DropdownMenu.
 */

test('top-nav navigates between primary routes', async ({ page }) => {
  await page.goto('/')

  // App heading + Library link visible in the new horizontal header.
  await expect(page.locator('header h1')).toHaveText('MAME Curator')
  await expect(
    page.getByRole('link', { name: 'Library', exact: true }),
  ).toBeVisible()

  // Settings + Help direct nav (exact: true avoids the "Open Settings"
  // link that may appear in the setup-check banner)
  await page.getByRole('link', { name: 'Settings', exact: true }).click()
  await expect(page).toHaveURL(/\/settings$/)

  await page.getByRole('link', { name: 'Help', exact: true }).click()
  await expect(page).toHaveURL(/\/help$/)

  // Back to Library
  await page.getByRole('link', { name: 'Library', exact: true }).click()
  await expect(page).toHaveURL(/\/$/)
})

test('More menu reveals secondary routes (Sessions / Activity / Stats)', async ({
  page,
}) => {
  await page.goto('/')

  // Open the More dropdown
  await page.getByRole('button', { name: 'More' }).click()

  // Click Sessions inside the menu
  await page.getByRole('menuitem', { name: 'Sessions' }).click()
  await expect(page).toHaveURL(/\/sessions$/)

  // Open More again, navigate to Stats
  await page.goto('/') // back to library to reset the menu state
  await page.getByRole('button', { name: 'More' }).click()
  await page.getByRole('menuitem', { name: 'Stats' }).click()
  await expect(page).toHaveURL(/\/stats$/)
})
