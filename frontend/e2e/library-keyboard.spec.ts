import { expect, test, type Page } from "@playwright/test";

/**
 * mame-curator-1144 review, Group 2 — the Library by keyboard alone, and what
 * jsdom cannot show: real focus, a visible ring, real scrolling. The fixture
 * has six games, so a long list is served from one of them. Run as guide-flow
 * is: `cd frontend && npm run build && npm run e2e`.
 */
const SEEN = "mame-curator:guide-seen:v1";
const VIEW = "mame-curator:library-view:v1";
const SIZE = "mame-curator:text-size:v1";
const CART = "mame-curator:cart:v1";

function storage(items: Record<string, string>) {
  return {
    cookies: [],
    origins: [
      {
        origin: "http://127.0.0.1:4173",
        localStorage: Object.entries({ [SEEN]: "true", ...items }).map(
          ([name, value]) => ({ name, value }),
        ),
      },
    ],
  };
}

/** Answers the games list, or a family, with `count` copies of a real card. */
async function serveMany(page: Page, count: number) {
  const copies = (item: object) =>
    Array.from({ length: count }, (_, i) => ({
      ...item,
      short_name: `g${i}`,
      description: `Game ${i}`,
      badges: [],
    }));
  await page.route("**/api/games?*", async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    await route.fulfill({
      response,
      json: { ...body, items: copies(body.items[0]), total: count },
    });
  });
  await page.route("**/api/games/*/alternatives*", async (route) => {
    const games = await (
      await page.request.get("/api/games?page=1&page_size=1")
    ).json();
    await route.fulfill({ json: { items: copies(games.items[0]) } });
  });
}

const card = (page: Page, i: number) =>
  page.getByRole("button", { name: `Game ${i}`, exact: true });
const add = (page: Page, i: number) =>
  page.getByRole("button", { name: `Add Game ${i} to cart` });

/** The widest solid ring in an element's box-shadow, in pixels. */
async function ringWidth(page: Page, name: string) {
  const shadow = await page
    .getByRole("button", { name, exact: true })
    .evaluate((el) => getComputedStyle(el).boxShadow);
  const widths = [...shadow.matchAll(/([\d.]+)px(?=,|$)/g)].map((m) =>
    Number(m[1]),
  );
  return Math.max(0, ...widths);
}

test.describe("the grid by keyboard", () => {
  test.use({
    viewport: { width: 1280, height: 800 },
    storageState: storage({ [VIEW]: "simple" }),
  });

  test.beforeEach(async ({ page }) => {
    await serveMany(page, 60);
    await page.goto("/");
    await expect(card(page, 0)).toBeVisible();
  });

  test("arrows move real focus and a plain ring, and bring the card into view", async ({
    page,
  }) => {
    await card(page, 0).focus();
    await page.keyboard.press("ArrowRight");
    await expect(card(page, 1)).toBeFocused();
    expect(await ringWidth(page, "Game 1")).toBeGreaterThanOrEqual(4);
    expect(await ringWidth(page, "Game 0")).toBe(0);

    for (let i = 0; i < 3; i++) await page.keyboard.press("ArrowDown");
    await expect(card(page, 10)).toBeFocused();
    await expect(card(page, 10)).toBeInViewport();

    await page.keyboard.press("End");
    await expect(card(page, 59)).toBeFocused();
    await expect(card(page, 59)).toBeInViewport();
    await page.keyboard.press("Home");
    await expect(card(page, 0)).toBeFocused();
    await expect(card(page, 0)).toBeInViewport();
  });

  test("scrolling away keeps focus in the grid, and an arrow comes back", async ({
    page,
  }) => {
    await card(page, 0).focus();
    await page.getByTestId("library-grid").evaluate((grid) => {
      grid.scrollTop = grid.scrollHeight;
    });
    await expect(card(page, 59)).toBeInViewport();
    await expect(card(page, 0)).toBeFocused();
    await page.keyboard.press("ArrowDown");
    await expect(card(page, 3)).toBeFocused();
    await expect(card(page, 3)).toBeInViewport();
  });

  test("Tab reaches one card and its Add, then leaves the grid", async ({
    page,
  }) => {
    // The last stop before the grid: the fixture has no listxml, so its banner.
    await page.getByRole("link", { name: "Open Settings" }).focus();
    await page.keyboard.press("Tab");
    await expect(card(page, 0)).toBeFocused();
    await page.keyboard.press("Tab");
    await expect(add(page, 0)).toBeFocused();
    await page.keyboard.press("Tab");
    await expect(page.locator("footer :focus")).toHaveCount(1);
  });

  test("Enter opens the game that has focus, and Esc comes back to it", async ({
    page,
  }) => {
    const opened: string[] = [];
    page.on("request", (r) => {
      const m = /\/api\/games\/([^/]+)\/alternatives/.exec(r.url());
      if (m) opened.push(m[1]!);
    });
    await card(page, 0).focus();
    await page.keyboard.press("ArrowRight");
    await page.keyboard.press("Enter");
    await expect(page.getByRole("dialog")).toBeVisible();
    expect(opened).toEqual(["g1"]);
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toBeHidden();
    await expect(card(page, 1)).toBeFocused();
  });

  test("Enter and Space on Add add the game and open nothing", async ({
    page,
  }) => {
    await add(page, 0).focus();
    await page.keyboard.press("Enter");
    await card(page, 0).focus();
    await page.keyboard.press("ArrowRight");
    await page.keyboard.press("Tab");
    await expect(add(page, 1)).toBeFocused();
    await page.keyboard.press("Space");
    await expect(page.locator("footer").getByText(/2/).first()).toBeVisible();
    await expect(page.getByRole("dialog")).toBeHidden();
    const cart = await page.evaluate((key) => localStorage.getItem(key), CART);
    expect(
      JSON.parse(cart!).map((i: { shortName: string }) => i.shortName),
    ).toEqual(["g0", "g1"]);
  });

  test("Ctrl combinations write nothing and move nothing, and Ctrl+K is the palette's", async ({
    page,
  }) => {
    const writes: string[] = [];
    page.on("request", (r) => {
      if (r.method() !== "GET") writes.push(r.url());
    });
    await card(page, 0).focus();
    await page.keyboard.press("ArrowDown");
    await expect(card(page, 3)).toBeFocused();
    await page.keyboard.press("Control+s");
    await page.keyboard.press("Control+o");
    await expect(card(page, 3)).toBeFocused();
    await expect(page.getByRole("dialog")).toBeHidden();

    await page.keyboard.press("Control+k");
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toBeHidden();
    // K alone moves up a row. With Ctrl, the active card has not moved.
    await expect(card(page, 3)).toHaveAttribute("tabindex", "0");
    expect(writes).toEqual([]);
  });
});

test.describe("the versions panel at the largest size", () => {
  test.use({
    viewport: { width: 1280, height: 800 },
    storageState: storage({ [VIEW]: "simple", [SIZE]: "largest" }),
  });

  test("scrolls, keeps the highlighted row in view, and reaches Launch", async ({
    page,
  }) => {
    await serveMany(page, 15);
    await page.goto("/");
    await card(page, 0).click();
    const panel = page.getByRole("dialog");
    await expect(panel.locator("[data-highlighted]")).toBeVisible();
    const [scrollH, clientH] = await panel.evaluate((el) => [
      el.scrollHeight,
      el.clientHeight,
    ]);
    expect(scrollH).toBeGreaterThan(clientH);

    for (let i = 0; i < 14; i++) await page.keyboard.press("ArrowDown");
    const row = panel.locator("[data-highlighted]");
    await expect(row).toContainText("Game 14");
    await expect(row).toBeInViewport({ ratio: 0.9 });
    const ring = await row.evaluate((el) => getComputedStyle(el).boxShadow);
    expect(ring, "the ring is drawn inside, where nothing clips it").toMatch(
      /inset/,
    );
    for (let i = 0; i < 14; i++) await page.keyboard.press("ArrowUp");
    await expect(row).toContainText("Game 0");
    await expect(row).toBeInViewport({ ratio: 0.9 });

    const launch = panel.getByRole("button", { name: /launch/i });
    await launch.scrollIntoViewIfNeeded();
    await expect(launch).toBeInViewport();
  });
});

for (const view of ["simple", "full"] as const) {
  test.describe(`the ${view} Library with an open cart at the largest size`, () => {
    test.use({
      viewport: { width: 1280, height: 800 },
      storageState: storage({
        [VIEW]: view,
        [SIZE]: "largest",
        [CART]: JSON.stringify(
          Array.from({ length: 40 }, (_, i) => ({ shortName: `g${i}` })),
        ),
      }),
    });

    test("the games keep their height, and a closed cart changes nothing", async ({
      page,
    }) => {
      await page.goto("/");
      const grid = page.getByTestId("library-grid");
      await expect(grid).toBeVisible();
      const main = page.locator("#main");
      // Closed: everything fits, and the copy bar is on screen.
      const closed = await main.evaluate((el) => [
        el.scrollHeight,
        el.clientHeight,
      ]);
      expect(closed[0]).toBeLessThanOrEqual(closed[1]!);

      const toggle = page.locator('[aria-controls="cart-panel"]');
      await toggle.click();
      await expect(page.locator("#cart-panel")).toBeVisible();
      await expect(toggle).toBeInViewport();

      const area = await grid.evaluate(
        (el) => el.parentElement!.getBoundingClientRect().height,
      );
      expect(area, "height of the games area").toBeGreaterThanOrEqual(480);

      await main.evaluate((el) => {
        el.scrollTop = 0;
      });
      await grid.evaluate((el) => el.scrollIntoView({ block: "nearest" }));
      await expect(page.locator('[role="gridcell"]').first()).toBeInViewport();

      await toggle.click();
      await expect(page.locator("#cart-panel")).toBeHidden();
      await expect
        .poll(() => main.evaluate((el) => el.scrollHeight <= el.clientHeight))
        .toBe(true);
    });
  });
}

test.describe("headings", () => {
  test.use({ storageState: storage({}) });

  test("a guide step has one top-level heading", async ({ page }) => {
    await page.goto("/start");
    await expect(page.getByTestId("guide-step")).toBeVisible();
    await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1);
  });
});
