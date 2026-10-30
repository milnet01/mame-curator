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
