import { expect, test } from '@playwright/test'

/**
 * FP26-Q / -R / -S / -T — UX walkthroughs validating the FP25
 * user-facing changes end-to-end. Pairs with the unit tests that
 * lock the same contracts at the component level:
 *
 *   FP25-G (apiErrorToast 1500 ms dedup window) — `Q`
 *   FP25-H (LibraryErrorPanel Retry disabled while refetch)  — `R`
 *   FP25-I/J (HelpPage scoped DOMPurify + deterministic data-URL) — `S`
 *   FP25-K(12) (SettingsPage snapshotRestoreError lifetime) — `T`
 *     [folds into FP26-L "drop the no-op" — UX shape is what the
 *      user actually experiences; the test pins observed behaviour
 *      regardless of whether the conditional stays or is dropped]
 */

// ---- FP26-Q: cold-start outage produces ONE toast, not nine ----------------

test('FP26-Q: cold-start backend outage produces one toast (FP25-G dedup window)', async ({
  page,
}) => {
  // Fail every /api/* call with a 500 to mimic a cold-start outage
  // where the LibraryPage's fan-out of nine queries (six tile counts
  // + games + facets + config + sessions + setupCheck) all fail
  // near-simultaneously. Pre-FP25-G the user saw nine stacked toasts;
  // FP25-G's 1500 ms dedup window collapses identical (code, detail)
  // pairs to one. Using 500 (not abort) so the response goes through
  // `rejectIfErrorResponse` and lands as ApiError with a uniform
  // (code='internal_error', detail='backend unavailable') key shape.
  await page.route('**/api/**', (route) =>
    route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 'internal_error',
        detail: 'backend unavailable',
        fields: [],
      }),
    }),
  )

  await page.goto('/')

  // The dedup window is 1500 ms — wait long enough for the burst to
  // complete and the deduper to skip duplicates.
  await page.waitForTimeout(2500)

  // Sonner renders each toast as a `<li data-sonner-toast>` inside
  // `[data-sonner-toaster]`. After FP25-G dedup, exactly one survives.
  const toasts = page.locator('[data-sonner-toast]')
  await expect(toasts).toHaveCount(1)
})

// ---- FP26-R: LibraryErrorPanel Retry disables while refetch in-flight ------

test('FP26-R+V: LibraryErrorPanel unmounts on Retry — FP25-H affordance never visible (FP26-V finding)', async ({
  page,
}) => {
  // FP26-V — UX bug surfaced by this walkthrough that the FP25-H
  // unit test missed: clicking Retry calls `games.refetch()`, react-
  // query resets `isError` to false for the duration of the in-flight
  // refetch, LibraryPage's `{games.isError ? <Panel/> : <Grid/>}`
  // ternary unmounts the panel, and the user sees nothing happen
  // (the empty grid takes over until refetch settles). FP25-H's
  // `disabled={isFetching}` plumbing is correct at the component
  // level, but the panel hosting the button is GONE during the
  // window that would have shown the disabled state.
  //
  // Fix (FP26-V): make the panel sticky while a refetch from an
  // errored state is in flight — e.g. `games.isError || (games.
  // isFetching && games.errorUpdateCount > 0)`. Until that lands,
  // this test captures the observed (buggy) behavior so a future
  // commit that fixes FP26-V flips the assertions.
  await page.route('**/api/games?**', async (route) => {
    await new Promise((r) => setTimeout(r, 1200))
    await route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 'internal_error',
        detail: 'forced 500',
        fields: [],
      }),
    })
  })

  await page.goto('/')

  const panel = page.getByRole('alert')
  await expect(panel).toBeVisible({ timeout: 10000 })
  const retry = page.getByRole('button', { name: /try again/i })
  await expect(retry).toBeEnabled()

  await retry.click()
  // CURRENT BUGGY BEHAVIOR (FP26-V): the panel unmounts on Retry.
  // No "Retrying…" label is ever shown to the user. The grid empty
  // state appears in the panel's place until refetch settles to
  // error again. This is the FP26-V finding the walkthrough caught.
  await expect(panel).toBeHidden({ timeout: 3000 })

  // After refetch settles (1.2s + ~1s retry exponential + 1.2s = ~3.5s)
  // the panel returns. The user sees a brief flicker, not an in-flight
  // affordance.
  await expect(panel).toBeVisible({ timeout: 10000 })
})

// ---- FP26-S: HelpPage DOMPurify scoping + deterministic data-URL -----------

test('FP26-S: HelpPage sanitizes data: URLs and adds rel-noopener (FP25-I/J)', async ({
  page,
}) => {
  // Mock the help endpoints so the rendered article carries the
  // attacker-shaped payloads we want DOMPurify to neutralise: a
  // <script>, a data:-URL <img>, a target="_blank" anchor without
  // rel. The fixture backend has an empty help dir, so without
  // mocks the article wouldn't render at all.
  await page.route('**/api/help/index', (route) =>
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        topics: [{ slug: 'fp26-s', title: 'FP26-S sanitization probe' }],
      }),
    }),
  )
  await page.route('**/api/help/fp26-s', (route) =>
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        slug: 'fp26-s',
        title: 'FP26-S sanitization probe',
        html: [
          '<h1>probe</h1>',
          '<script>window.PWND = true</script>',
          '<a href="https://example.com" target="_blank">external link</a>',
          '<img src="data:image/png;base64,iVBORw0KGgo=" alt="datapayload" />',
          '<p>safe paragraph</p>',
        ].join('\n'),
      }),
    }),
  )

  await page.goto('/help?topic=fp26-s')

  const article = page.locator('article')
  await expect(article).toBeVisible({ timeout: 5000 })
  // Anchor on the safe paragraph so we know the article body rendered.
  await expect(article.getByText('safe paragraph')).toBeVisible()

  // FP25-I assertion: <script> is stripped regardless of how the
  // upstream markdown attempted to inject one. AND no global
  // side-effect from a leaked DOMPurify hook fires (window.PWND
  // would only be set if the script ran).
  await expect(article.locator('script')).toHaveCount(0)
  const pwned = await page.evaluate(
    () => (window as unknown as { PWND?: boolean }).PWND === true,
  )
  expect(pwned).toBe(false)

  // FP25-I (scoped DOMPurify hook): the target="_blank" anchor
  // survives WITH `rel="noopener noreferrer"` injected by the
  // afterSanitizeAttributes hook on the scoped instance.
  const externalLink = article.getByRole('link', { name: 'external link' })
  await expect(externalLink).toHaveAttribute('target', '_blank')
  await expect(externalLink).toHaveAttribute('rel', 'noopener noreferrer')

  // FP25-J assertion: the data: <img> survives with NO src (the
  // deterministic outcome the strengthened FP25-J test pins).
  const dataImg = article.locator('img[alt="datapayload"]')
  // The img element survives but its src has been stripped to empty
  // or removed entirely. Either outcome is acceptable per FP25-J.
  if ((await dataImg.count()) > 0) {
    const src = await dataImg.getAttribute('src')
    expect(src ?? '').not.toMatch(/^data:/i)
  }
})

// ---- FP26-T: settings restore failure surfaces the alert ------------------

test('FP26-T: settings restore failure surfaces the alert (FP25-K(12) UX shape)', async ({
  page,
}) => {
  // Stub the snapshots list endpoint with one fake entry so the
  // SnapshotsTab has something to render a Restore button against.
  await page.route('**/api/config/snapshots', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        items: [
          {
            id: '2026-05-11T08-30-00Z',
            ts: '2026-05-11T08:30:00Z',
            files: ['config.yaml', 'overrides.yaml', 'sessions.yaml', 'notes.json'],
          },
        ],
      }),
    })
  })
  // Force the restore mutation to fail with a 422 carrying a
  // detail string the SettingsPage's snapshotRestoreError surface
  // should render.
  await page.route('**/api/config/snapshots/*/restore', async (route) => {
    await route.fulfill({
      status: 422,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 'snapshot_corrupt',
        detail: 'snapshot integrity check failed',
        fields: [],
      }),
    })
  })

  await page.goto('/settings')

  // The Settings page uses defaultValue="paths" on its Tabs — switch
  // to the Snapshots tab by clicking the tab trigger first.
  await page.getByRole('tab', { name: /snapshots/i }).click()

  // Click the first Restore button (label per SnapshotsTab spec).
  const restore = page.getByRole('button', { name: /restore/i }).first()
  await expect(restore).toBeVisible({ timeout: 5000 })
  await restore.click()

  // The ConfirmationDialog surfaces — confirm the destructive
  // action so the mutation actually fires.
  const confirm = page.getByRole('button', { name: /restore \d+ file/i })
  await expect(confirm).toBeVisible({ timeout: 5000 })
  await confirm.click()

  // The persistent alert surfaces with the detail string we returned
  // (FP20-J surface; FP25-K(12) governs lifetime — see FP26-L for
  // the no-op verdict). Scope to the role=alert element so we match
  // the inline persistent surface, NOT the transient Sonner toast
  // which renders the same text in the Notifications region.
  const alertRegion = page.locator('main [role="alert"]')
  await expect(alertRegion).toBeVisible({ timeout: 5000 })
  await expect(alertRegion).toContainText(/snapshot integrity check failed/i)
})
