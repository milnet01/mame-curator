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

test('FP27 A6b — `/` focuses the library search input', async ({ page }) => {
  // Pre-fix: no useKeyboard binding for `/`; dispatching `/` types the
  // literal character into whatever has focus (or does nothing).
  // Post-fix: a useKeyboard binding at the LibraryPage level focuses
  // `#filters-search` regardless of which element had focus before.
  await page.goto('/')

  // Make sure nothing relevant has focus going in. Click the body so the
  // dispatch isn't already aimed at an input.
  await page.locator('body').click()
  await page.keyboard.press('/')

  // Allow the focus handler to settle (useKeyboard binds via
  // document.addEventListener('keydown'), the handler then synchronously
  // calls .focus() — single tick).
  await expect(page.locator('#filters-search')).toBeFocused()
})
