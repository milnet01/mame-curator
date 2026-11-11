import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { keepCompilations, keepLanguages } from "./guideSteps";

/**
 * mame-curator-1144 — the guide in a real browser. local-CI.sh runs
 * frontend/e2e before every push; by hand: `cd frontend && npm run build && npm
 * run e2e`.
 *
 * INV-6: a repeat copy adds to the existing playlist. The fixture's ROM
 * folders are empty stubs, so this seeds a zip per winner and an old playlist.
 * INV-10: at the largest text size, nothing scrolls sideways and no card
 * title is cut off by its row.
 */
const e2eData = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "fixtures/data/e2e",
);
const sourceRoms = path.join(e2eData, "source-roms");
const destRoms = path.join(e2eData, "dest-roms");
const playlist = path.join(e2eData, "mame.lpl");

const SEEN = "mame-curator:guide-seen:v1";
const VIEW = "mame-curator:library-view:v1";
const SIZE = "mame-curator:text-size:v1";

function localStorageState(items: Record<string, string>) {
  return {
    cookies: [],
    origins: [
      {
        origin: "http://127.0.0.1:4173",
        localStorage: Object.entries(items).map(([name, value]) => ({
          name,
          value,
        })),
      },
    ],
  };
}

test.describe("INV-6: a repeat copy", () => {
  test.use({ storageState: localStorageState({}) });

  let seeded: string[] = [];

  test.afterEach(() => {
    for (const name of seeded) {
      fs.rmSync(path.join(sourceRoms, `${name}.zip`), { force: true });
      fs.rmSync(path.join(destRoms, `${name}.zip`), { force: true });
    }
    fs.rmSync(playlist, { force: true });
  });

  test("adds to the existing playlist and keeps its old entry", async ({
    page,
    request,
  }) => {
    const games = await (
      await request.get("/api/games?page=1&page_size=500")
    ).json();
    seeded = games.items.map((g: { short_name: string }) => g.short_name);
    expect(seeded.length).toBeGreaterThan(0);
    fs.mkdirSync(destRoms, { recursive: true });
    for (const name of seeded) {
      fs.writeFileSync(path.join(sourceRoms, `${name}.zip`), name);
    }
    fs.writeFileSync(
      playlist,
      JSON.stringify({
        items: [{ path: "/roms/oldgame.zip", label: "Old Game" }],
      }),
    );

    await page.goto("/");
    await expect(page).toHaveURL(/\/start$/);
    await page
      .getByRole("button", { name: "The best version of every game" })
      .click();
    await keepCompilations(page);
    await keepLanguages(page);
    await page.getByRole("button", { name: "Copy these" }).click();
    await page.getByRole("button", { name: "Yes, copy here" }).click();
    await expect(
      page.getByText("These will be added to your existing game list."),
    ).toBeVisible();
    await page.getByRole("button", { name: "Start copying" }).click();
    await expect(
      page.getByRole("heading", { name: "Your games are copied." }),
    ).toBeVisible({ timeout: 15_000 });

    const items: { path: string }[] = JSON.parse(
      fs.readFileSync(playlist, "utf-8"),
    ).items;
    const paths = items.map((i) => i.path);
    expect(paths.some((p) => p.endsWith("oldgame.zip"))).toBe(true);
    for (const name of seeded) {
      expect(paths.some((p) => p.endsWith(`${name}.zip`))).toBe(true);
    }
  });
});

/** Holds matching requests until the returned function is called. */
async function holdRoute(page: Page, match: (url: URL) => boolean) {
  let release = () => {};
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route(
    (url) => match(url),
    async (route) => {
      await held;
      await route.continue().catch(() => {});
    },
  );
  return release;
}

const listFetch = (url: URL) =>
  url.pathname === "/api/games" && url.searchParams.get("page_size") === "500";
const countFetch = (url: URL) =>
  url.pathname === "/api/games" && url.searchParams.get("page_size") === "1";

/** The text of each element that gains focus from now on. */
async function recordFocus(page: Page) {
  await page.evaluate(() => {
    const heard: string[] = [];
    (window as unknown as { heard: string[] }).heard = heard;
    document.addEventListener("focusin", (e) =>
      heard.push((e.target as HTMLElement).textContent ?? ""),
    );
  });
  return () =>
    page.evaluate(() => (window as unknown as { heard: string[] }).heard);
}

test.describe("the guide is honest and audible", () => {
  test.use({ storageState: localStorageState({ [SEEN]: "true" }) });

  test("INV-2: a heading that changes gets a real focus event", async ({
    page,
  }) => {
    const release = await holdRoute(page, countFetch);
    await page.goto("/start");
    await expect(
      page.getByRole("heading", { name: "Which games would you like?" }),
    ).toBeFocused();
    await page
      .getByRole("button", { name: "The best version of every game" })
      .click();
    await keepCompilations(page);
    await keepLanguages(page);
    const counting = page.getByRole("heading", {
      name: "Counting the games…",
    });
    await expect(counting).toBeFocused();
    const heard = await recordFocus(page);

    release();

    const found = page.getByRole("heading", { name: /^This finds/ });
    await expect(found).toBeFocused();
    expect(await heard()).toEqual([await found.textContent()]);
  });

  test("INV-5: Back during the name fetch sticks", async ({ page }) => {
    const release = await holdRoute(page, listFetch);
    await page.goto("/start");
    await page
      .getByRole("button", { name: "The best version of every game" })
      .click();
    await keepCompilations(page);
    await keepLanguages(page);
    await page.getByRole("button", { name: "Copy these" }).click();
    await page.getByRole("button", { name: "Back" }).click();
    const previous = page.getByRole("heading", {
      name: "Which languages can you read?",
    });
    await expect(previous).toBeFocused();

    release();
    await page.waitForTimeout(300);

    await expect(previous).toBeFocused();
  });

  test("the Check report is heard, and a failed start keeps its place", async ({
    page,
  }) => {
    let finishDryRun = () => {};
    const dryRunHeld = new Promise<void>((resolve) => {
      finishDryRun = resolve;
    });
    await page.route("**/api/copy/dry-run", async (route) => {
      await dryRunHeld;
      await route.fulfill({
        json: {
          counts: {
            selected: 2,
            bios: 3,
            bios_missing_source: 1,
            missing_source: 0,
            already_copied: 0,
            new: 2,
          },
          summary: {
            dest_writable: true,
            free_space_gap_bytes: 1000,
            existing_playlist: false,
          },
        },
      });
    });
    let finishStart = () => {};
    const startHeld = new Promise<void>((resolve) => {
      finishStart = resolve;
    });
    await page.route("**/api/copy/start", async (route) => {
      await startHeld;
      await route.fulfill({
        status: 500,
        json: { code: "boom", detail: "it broke", fields: [] },
      });
    });

    await page.goto("/start");
    await page
      .getByRole("button", { name: "The best version of every game" })
      .click();
    await keepCompilations(page);
    await keepLanguages(page);
    await page.getByRole("button", { name: "Copy these" }).click();
    await page.getByRole("button", { name: "Yes, copy here" }).click();
    await expect(
      page.getByRole("heading", { name: "Checking your folders…" }),
    ).toBeFocused();
    const report = page.getByRole("status");
    await expect(report).toBeEmpty();
    const heard = await recordFocus(page);

    finishDryRun();

    await expect(
      page.getByRole("heading", { name: "Ready to copy?" }),
    ).toBeFocused();
    expect(await heard()).toEqual(["Ready to copy?"]);
    await expect(report).toContainText("2 BIOS files these games need will");
    await expect(report).toContainText(
      "1 BIOS file these games need is not in your ROM folder",
    );

    const start = page.getByRole("button", { name: "Start copying" });
    await start.focus();
    await page.keyboard.press("Enter");
    await expect(start).toBeDisabled();
    await expect(report).toContainText("Starting the copy…");
    await expect(page.getByRole("button", { name: "Back" })).toHaveCount(0);

    finishStart();

    await expect(page.getByRole("alert")).toContainText("it broke");
    await expect(start).toBeEnabled();
    await expect(start).toBeFocused();
    await expect(page.getByRole("button", { name: "Back" })).toBeVisible();
  });
});

async function expectNoSidewaysScroll(page: Page, selector: string) {
  const [scrollWidth, clientWidth] = await page
    .locator(selector)
    .first()
    .evaluate((el) => [el.scrollWidth, el.clientWidth]);
  expect(scrollWidth, `${selector} scrolls sideways`).toBeLessThanOrEqual(
    clientWidth,
  );
}

async function rowHeight(page: Page) {
  const row = page.locator('[data-testid="library-grid"] [role="row"]').first();
  await expect(row).toBeVisible();
  return row.evaluate((el) => el.getBoundingClientRect().height);
}

/** Every visible card's text must end inside the card's own row. */
async function expectTitlesInsideRows(page: Page) {
  const cut = await page
    .locator('[data-testid="library-grid"] [role="gridcell"]')
    .evaluateAll((cells) =>
      cells.flatMap((cell) => {
        const row = cell.closest('[role="row"]')!.getBoundingClientRect();
        return [...cell.querySelectorAll("h3, h4, p, span")]
          .filter((el) => (el.textContent ?? "").trim() !== "")
          .filter((el) => el.getBoundingClientRect().bottom > row.bottom + 0.5)
          .map((el) => el.textContent);
      }),
    );
  expect(cut, "text cut off by its row").toEqual([]);
}

for (const view of ["simple", "full"] as const) {
  test.describe(`INV-10: the ${view} Library at the largest size`, () => {
    test.use({
      viewport: { width: 1280, height: 800 },
      storageState: localStorageState({
        [SEEN]: "true",
        [VIEW]: view,
        [SIZE]: "largest",
      }),
    });

    test("scrolls one way only, and rows hold their titles", async ({
      page,
    }) => {
      await page.goto("/");
      await expect(page.getByTestId("library-grid")).toBeVisible();
      const atLargest = await rowHeight(page);

      await expectNoSidewaysScroll(page, "#main");
      await expectNoSidewaysScroll(page, "header");
      await expectNoSidewaysScroll(page, '[data-testid="library-grid"]');
      await expectTitlesInsideRows(page);

      await page.getByLabel("Text size").selectOption("normal");
      await expect.poll(() => rowHeight(page)).toBeCloseTo(atLargest / 2, 0);
    });
  });
}

test.describe("INV-10: the guide at the largest size", () => {
  test.use({
    viewport: { width: 1280, height: 800 },
    storageState: localStorageState({ [SEEN]: "true", [SIZE]: "largest" }),
  });

  test("scrolls one way only", async ({ page }) => {
    await page.goto("/start");
    await expect(page.getByTestId("guide-step")).toBeVisible();
    await expectNoSidewaysScroll(page, "#main");
    await expectNoSidewaysScroll(page, "header");
    await page.getByRole("button", { name: "A ready-made group" }).click();
    await expect(
      page.getByRole("heading", { name: "Which group?" }),
    ).toBeFocused();
    await expectNoSidewaysScroll(page, "#main");
  });
});

test.describe("mame-curator-1210: at 320px, about 400% zoom", () => {
  test.use({
    viewport: { width: 320, height: 400 },
    storageState: localStorageState({ [SEEN]: "true", [VIEW]: "simple" }),
  });

  test("the page scrolls down as a whole, never sideways", async ({ page }) => {
    for (const route of ["/start", "/"]) {
      await page.goto(route);
      await expect(page.locator("#main")).not.toBeEmpty();
      const mainScrolls = await page
        .locator("#main")
        .evaluate((el) => getComputedStyle(el).overflowY);
      expect(mainScrolls, `${route}: <main> scrolls on its own`).toBe(
        "visible",
      );
    }
    // The Library's own check is mame-curator-1213's, below.
    await page.goto("/start");
    await expect(page.getByTestId("guide-step")).toBeVisible();
    await expectNoSidewaysScroll(page, "html");
    await expect(
      page.getByRole("button", { name: "Go to a page or help topic" }),
    ).toBeVisible();

    // The Library is one window tall, so its game list has room to fill.
    await page.goto("/");
    const grid = page.getByTestId("library-grid");
    await expect(grid).toBeVisible();
    const height = await grid.evaluate((el) => el.clientHeight);
    expect(height).toBeGreaterThanOrEqual(400 * 0.6 - 1);
  });
});

test.describe("mame-curator-1213: the Library at 320px", () => {
  test.use({
    viewport: { width: 320, height: 400 },
    storageState: localStorageState({
      [SEEN]: "true",
      [VIEW]: "simple",
      // A game in the cart, so the cart bar shows its longest words.
      "mame-curator:cart:v1": JSON.stringify([{ shortName: "pacman" }]),
    }),
  });

  test("the search box and the cart bar fit the window", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("simple-library-bar")).toBeVisible();
    await expect(page.getByTestId("library-grid")).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Copy", exact: true }),
    ).toBeVisible();
    await expectNoSidewaysScroll(page, "html");
  });
});

test.describe("mame-curator-1216: Hide compilations?", () => {
  test.use({ storageState: localStorageState({ [SEEN]: "true" }) });

  const fixtureConfig = path.resolve(e2eData, "../../config.yaml");
  let original = "";

  test.beforeEach(() => {
    original = fs.readFileSync(fixtureConfig, "utf-8");
  });

  // The answer is saved to the fixture config, so put the server and the
  // file back as they were.
  test.afterEach(async ({ request }) => {
    const config = await (await request.get("/api/config")).json();
    await request.patch("/api/config", {
      data: { filters: { ...config.filters, drop_multigame: false } },
    });
    fs.writeFileSync(fixtureConfig, original);
  });

  test("the answer is saved, and the guide counts on", async ({
    page,
    request,
  }) => {
    await page.goto("/start");
    await page
      .getByRole("button", { name: "The best version of every game" })
      .click();
    await expect(
      page.getByRole("heading", { name: "Hide compilations?" }),
    ).toBeFocused();
    await expect(page.getByText("Step 2 of 7")).toBeVisible();
    await expect(
      page.getByRole("button", { name: /^No, keep them/ }),
    ).toContainText("In use now");

    await page.getByRole("button", { name: /^Yes, hide them/ }).click();
    await keepLanguages(page);

    await expect(
      page.getByRole("heading", { name: /^This finds/ }),
    ).toBeFocused();
    await expect(page.getByText("Step 4 of 7")).toBeVisible();
    const config = await (await request.get("/api/config")).json();
    expect(config.filters.drop_multigame).toBe(true);
  });
});

test.describe("mame-curator-1217: Which languages can you read?", () => {
  test.use({ storageState: localStorageState({ [SEEN]: "true" }) });

  const fixtureConfig = path.resolve(e2eData, "../../config.yaml");
  let original = "";

  // The fixture has no languages.ini, so the list is empty; a kept language
  // is set first, so "Keep every language" has something to save.
  test.beforeEach(async ({ request }) => {
    original = fs.readFileSync(fixtureConfig, "utf-8");
    const config = await (await request.get("/api/config")).json();
    await request.patch("/api/config", {
      data: { filters: { ...config.filters, keep_languages: ["English"] } },
    });
  });

  test.afterEach(async ({ request }) => {
    const config = await (await request.get("/api/config")).json();
    await request.patch("/api/config", {
      data: { filters: { ...config.filters, keep_languages: [] } },
    });
    fs.writeFileSync(fixtureConfig, original);
  });

  test("Keep every language is saved, and the guide counts on", async ({
    page,
    request,
  }) => {
    await page.goto("/start");
    await page
      .getByRole("button", { name: "The best version of every game" })
      .click();
    await keepCompilations(page);
    await expect(
      page.getByRole("heading", { name: "Which languages can you read?" }),
    ).toBeFocused();
    await expect(page.getByText("Step 3 of 7")).toBeVisible();
    await expect(
      page.getByText("No languages are listed, so every language is kept."),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /^Keep every language/ }),
    ).not.toContainText("In use now");

    await keepLanguages(page);

    await expect(
      page.getByRole("heading", { name: /^This finds/ }),
    ).toBeFocused();
    await expect(page.getByText("Step 4 of 7")).toBeVisible();
    const config = await (await request.get("/api/config")).json();
    expect(config.filters.keep_languages).toEqual([]);
  });
});

test.describe("mame-curator-1218: the full Library at 320px", () => {
  test.use({
    viewport: { width: 320, height: 400 },
    storageState: localStorageState({ [SEEN]: "true", [VIEW]: "full" }),
  });

  test("the top bar fits the window, with every control on it", async ({
    page,
  }) => {
    await page.goto("/");
    await expect(page.getByTestId("library-grid")).toBeVisible();
    const fewer = page.getByRole("button", { name: "Fewer options" });
    const header = page.locator("header", { has: fewer });
    await expect(fewer).toBeVisible();
    await expect(page.getByTestId("library-walkthrough-toggle")).toBeVisible();
    const box = await header.boundingBox();
    expect(box, "the top bar is on the page").not.toBeNull();
    expect(box!.x).toBeGreaterThanOrEqual(0);
    expect(box!.x + box!.width).toBeLessThanOrEqual(320);
    await expectNoSidewaysScroll(page, "html");

    // Stacked, not squeezed: the page scrolls down to the end of the
    // filters, and the game list keeps room to show games.
    const lastFilter = page.getByRole("button", { name: "Save as session" });
    await lastFilter.scrollIntoViewIfNeeded();
    await expect(lastFilter).toBeInViewport();
    const grid = page.getByTestId("library-grid");
    await grid.scrollIntoViewIfNeeded();
    const height = await grid.evaluate((el) => el.clientHeight);
    expect(height).toBeGreaterThanOrEqual(400 * 0.6 - 1);
    const firstGame = grid.getByRole("button", { name: /Pac-Man/ }).first();
    await firstGame.scrollIntoViewIfNeeded();
    await expect(firstGame).toBeInViewport();
  });

  test("mame-curator-1223: only the game list scrolls inside the page, and it fits the window", async ({
    page,
  }) => {
    await page.goto("/");
    await expect(page.getByTestId("library-grid")).toBeVisible();
    // Every box below <html> that scrolls up and down on its own.
    const scrollers = await page.evaluate(() =>
      [...document.querySelectorAll<HTMLElement>("body *")]
        .filter((el) => {
          const y = getComputedStyle(el).overflowY;
          return (
            (y === "auto" || y === "scroll") &&
            el.scrollHeight > el.clientHeight + 1
          );
        })
        .map((el) => ({
          what:
            el.dataset.testid ??
            `${el.tagName.toLowerCase()}.${el.className}`.slice(0, 80),
          height: el.clientHeight,
        })),
    );
    expect(scrollers.map((s) => s.what)).toEqual(["library-grid"]);
    expect(scrollers[0].height).toBeLessThanOrEqual(400);
  });
});
