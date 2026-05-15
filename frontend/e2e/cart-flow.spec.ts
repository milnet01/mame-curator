import { expect, test } from '@playwright/test'

/**
 * P15 § F14 — cart-flow smoke.
 *
 * Goal: drive the new cart UX end-to-end against the real
 * fixture-backed backend. The mini DAT has only 6 machines so
 * the featured tiles' catver-keyed counts are likely 0 here
 * — we lean on clicking a card's +Add directly to populate
 * the cart instead of bulk-add.
 *
 * DS04 T2.13: dropped three unit-duplicate e2e tests that
 * `CartBar.test.tsx` + `CartPanel.test.tsx` already covered:
 * "expand chevron toggles cart panel; remove ✕ drops the row"
 * and "Copy button is disabled when cart is empty". Both were
 * pure component-level behaviour the unit tests pin
 * deterministically. The integration scenario below ('first visit
 * shows onboarding banner; +Add populates the cart') stays — it
 * exercises the wiring from add-button click → onboarding-banner
 * dismiss → cart-bar-count update → card-✓-Added flip, none of
 * which is covered at the unit level.
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

  // Click an Add button — pick the first card on the grid. Locator
  // auto-waits, so no explicit `waitForSelector` is needed.
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
