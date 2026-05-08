import { expect, test } from '@playwright/test'

/**
 * P15 § F14 — cart-flow smoke.
 *
 * Goal: drive the new cart UX end-to-end against the real
 * fixture-backed backend. The mini DAT has only 6 machines so
 * the featured tiles' catver-keyed counts are likely 0 here
 * — we lean on clicking a card's +Add directly to populate
 * the cart instead of bulk-add.
 */

test.beforeEach(async ({ context }) => {
  // Ensure each test starts with a clean cart + fresh onboarding banner.
  // localStorage is per-origin; clear for the test origin.
  await context.clearCookies()
  await context.addInitScript(() => {
    localStorage.clear()
  })
})

test('first visit shows onboarding banner; +Add populates the cart', async ({
  page,
}) => {
  await page.goto('/')

  // Onboarding banner visible on first mount.
  // FP24-Y: banner has no role (it's static instructional content,
  // not a live region). Match by visible text instead.
  const banner = page.getByText(/Tap a game to add it to your list/i)
  await expect(banner).toBeVisible()

  // Cart bar shows empty (footer-scoped to avoid ambiguity)
  await expect(page.locator('footer').getByText('Cart empty')).toBeVisible()

  // Wait for at least one Add button — the virtualizer needs to render cards.
  await page.waitForSelector('button[aria-label*="to cart"]', { timeout: 10000 })

  // Click an Add button — pick the first card on the grid
  const addButton = page
    .getByRole('button', { name: /add .+ to cart/i })
    .first()
  await addButton.click()

  // Banner auto-dismisses on first add
  await expect(banner).not.toBeVisible()

  // Cart bar now shows the game count (FP24-B dropped the GB figure
  // until per-cart-item byte sums exist).
  await expect(page.getByText(/^1 game/)).toBeVisible()

  // Card flips to ✓ Added (the same card we just clicked)
  await expect(page.getByText('✓ Added')).toBeVisible()
})

test('expand chevron toggles cart panel; remove ✕ drops the row', async ({
  page,
}) => {
  await page.goto('/')

  // Wait for cards to render, then add one game
  await page.waitForSelector('button[aria-label*="to cart"]', { timeout: 10000 })
  await page.getByRole('button', { name: /add .+ to cart/i }).first().click()
  await expect(page.getByText(/^1 game/)).toBeVisible()

  // Expand the cart
  await page.getByRole('button', { name: 'Expand cart' }).click()
  const panel = page.getByRole('region', { name: 'Cart contents' })
  await expect(panel).toBeVisible()

  // Remove the only row (the CartPanel aria-label is per-shortName, e.g.
  // "Remove pacman from cart"; the footer sticky bar also has a Copy button
  // labelled "Copy" — target the remove button inside the panel explicitly)
  await panel
    .getByRole('button', { name: /^remove .+ from cart$/i })
    .first()
    .click()

  // Cart bar back to empty — use the footer locator to be precise
  await expect(page.locator('footer').getByText('Cart empty')).toBeVisible()
})

test('Copy button is disabled when cart is empty', async ({ page }) => {
  await page.goto('/')
  // Locate the bottom-bar Copy button (not the "Copy" tab anywhere else).
  // It's inside a <footer>; use a footer-scoped role query.
  const footer = page.locator('footer').first()
  const copyBtn = footer.getByRole('button', { name: /^copy$/i })
  await expect(copyBtn).toBeDisabled()
})
