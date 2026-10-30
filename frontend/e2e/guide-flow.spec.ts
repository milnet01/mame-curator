import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

/**
 * mame-curator-1144 — the guide in a real browser. Run by hand: no gate runs
 * frontend/e2e, so `cd frontend && npm run build && npm run e2e`.
 *
 * INV-6: a repeat copy adds to the existing playlist. The fixture's ROM
 * folders are empty stubs, so this seeds a zip per winner and an old playlist.
 * INV-10: at the largest text size, nothing scrolls sideways and no card
 * title is cut off by its row.
 */
const e2eData = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../data/e2e",
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
    await page.getByRole("button", { name: "Copy these" }).click();
    await page.getByRole("button", { name: "Back" }).click();
    const which = page.getByRole("heading", {
      name: "Which games would you like?",
    });
    await expect(which).toBeFocused();

    release();
    await page.waitForTimeout(300);

    await expect(which).toBeFocused();
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
