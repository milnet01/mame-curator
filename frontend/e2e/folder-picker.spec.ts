import { expect, test, type Locator, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { keepCompilations, keepLanguages } from "./guideSteps";

/**
 * mame-curator-1145 INV-10, INV-12, mame-curator-1165, mame-curator-1171 —
 * what only a real browser can settle: whether the picker and its grant prompt
 * fit the window with a long path at large text, and where focus lands.
 * local-CI.sh runs frontend/e2e before every push; by hand: `cd frontend && npm
 * run build && npm run e2e`. The folder answers are stand-ins, so no test here
 * can grant anything.
 */
const SIZE = "mame-curator:text-size:v1";
const MEDIUM_PATH = "/mnt/Games/PC Games/Emulators/MAME/roms/arcade";
const LONG_PATH = `/mnt/${"a-very-long-folder-name-without-any-spaces/".repeat(5)}roms`;
const WINDOWS = [
  { width: 1280, height: 720 },
  { width: 800, height: 600 },
  { width: 400, height: 700 },
];

const entry = (name: string, is_dir: boolean, base = "/home/me") => ({
  name,
  path: `${base}/${name}`,
  is_dir,
  hidden: false,
  size: is_dir ? null : 1,
  mtime: "2026-05-01T00:00:00Z",
});

/** The picker's server answers; `blocked` is refused as outside the sandbox. */
async function folders(
  page: Page,
  { home = "/home/me", blocked = "", entries = [] as object[], roots = [""] },
) {
  await page.route("**/api/fs/home", (route) =>
    route.fulfill({ json: { path: home } }),
  );
  await page.route("**/api/fs/roots", (route) =>
    route.fulfill({ json: { roots: ["/"] } }),
  );
  await page.route("**/api/fs/allowed-roots", (route) =>
    route.fulfill({
      json: {
        roots: roots
          .filter(Boolean)
          .map((path, i) => ({ id: `r${i}`, path, source: "granted" })),
      },
    }),
  );
  await page.route("**/api/fs/list?*", (route) => {
    const path = new URL(route.request().url()).searchParams.get("path")!;
    if (path === blocked) {
      return route.fulfill({
        status: 403,
        json: { code: "fs_sandboxed", detail: "outside", fields: [] },
      });
    }
    return route.fulfill({ json: { path, parent: "/", entries } });
  });
}

async function setupMode(page: Page) {
  const reply = await page.request.get("/api/setup/check");
  const check = await reply.json();
  await page.route("**/api/setup/check", (route) =>
    route.fulfill({ json: { ...check, setup_required: true } }),
  );
}

/** Every box in the window, and nothing wider than the dialog holding it. */
async function fits(page: Page, dialog: Locator, parts: Locator[]) {
  const size = page.viewportSize()!;
  const box = (await dialog.boundingBox())!;
  expect(box.x, "dialog left").toBeGreaterThanOrEqual(0);
  expect(box.y, "dialog top").toBeGreaterThanOrEqual(0);
  expect(box.x + box.width, "dialog right").toBeLessThanOrEqual(size.width);
  expect(box.y + box.height, "dialog bottom").toBeLessThanOrEqual(size.height);
  const sideways = await dialog.evaluate(
    (el) => el.scrollWidth - el.clientWidth,
  );
  expect(sideways, "dialog scrolls sideways").toBeLessThanOrEqual(0);
  for (const part of parts) {
    await part.scrollIntoViewIfNeeded();
    const rect = (await part.boundingBox())!;
    expect(rect.x, "part left").toBeGreaterThanOrEqual(box.x);
    expect(rect.x + rect.width, "part right").toBeLessThanOrEqual(
      box.x + box.width + 0.5,
    );
    await expect(part).toBeInViewport({ ratio: 0.1 });
  }
}

for (const window of WINDOWS) {
  for (const size of ["large", "largest"]) {
    for (const path of [MEDIUM_PATH, LONG_PATH]) {
      const name = `${window.width}x${window.height}, ${size} text, a path of ${path.length}`;

      test(`the wizard's grant prompt fits at ${name}`, async ({ page }) => {
        await page.addInitScript(
          ([k, v]) => localStorage.setItem(k!, v!),
          [SIZE, size],
        );
        await page.setViewportSize(window);
        await setupMode(page);
        await folders(page, { home: path, blocked: path });
        await page.goto("/start");
        await page.getByRole("button", { name: "Choose a folder" }).click();
        const dialog = page.getByRole("alertdialog");
        await fits(page, dialog, [
          dialog.getByRole("heading"),
          dialog.getByText("cannot look in"),
          dialog.getByRole("button", { name: "Cancel" }),
          dialog.getByRole("button", { name: /^Allow / }),
        ]);
      });

      test(`the wizard's picker fits at ${name}`, async ({ page }) => {
        await page.addInitScript(
          ([k, v]) => localStorage.setItem(k!, v!),
          [SIZE, size],
        );
        await page.setViewportSize(window);
        await setupMode(page);
        await folders(page, {
          home: path,
          roots: [path],
          entries: [entry(path.replaceAll("/", "-"), true)],
        });
        await page.goto("/start");
        await page.getByRole("button", { name: "Choose a folder" }).click();
        const dialog = page.getByRole("dialog");
        await fits(page, dialog, [
          dialog.getByRole("heading"),
          dialog.getByRole("button", { name: path, exact: true }),
          dialog.locator("code"),
          dialog.getByRole("listitem").first(),
          dialog.getByRole("button", { name: "Use this folder" }),
          dialog.getByRole("button", { name: "Cancel" }),
        ]);
        const rows = dialog.locator("[data-testid=fs-entries]");
        const sideways = await rows.evaluate(
          (el) => el.scrollWidth - el.clientWidth,
        );
        expect(sideways, "rows scroll sideways").toBeLessThanOrEqual(0);
      });
    }
  }
}

test("the wizard's path line shows the end of a long path", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  await setupMode(page);
  await folders(page, { home: LONG_PATH });
  await page.goto("/start");
  await page.getByRole("button", { name: "Choose a folder" }).click();
  const line = page.getByRole("dialog").locator("code");
  const cut = await line.evaluate((el) => el.scrollWidth - el.clientWidth);
  expect(cut, "hidden pixels of the path").toBeLessThanOrEqual(0);
});

test("Settings' grant prompt fits too, with a long path", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  await folders(page, { home: LONG_PATH, blocked: LONG_PATH });
  await page.route("**/api/config", async (route) => {
    const reply = await route.fetch();
    const body = await reply.json();
    body.paths.source_roms = LONG_PATH;
    await route.fulfill({ response: reply, json: body });
  });
  await page.goto("/settings");
  await page.getByRole("button", { name: "Browse for Source ROMs" }).click();
  const dialog = page.getByRole("alertdialog");
  await fits(page, dialog, [
    dialog.getByRole("button", { name: "Cancel" }),
    dialog.getByRole("button", { name: /^Allow / }),
  ]);
});

test("Settings' picker gives focus back to Browse however it closes (mame-curator-1176)", async ({
  page,
}) => {
  await page.route("**/api/config", async (route) => {
    const reply = await route.fetch();
    const body = await reply.json();
    body.paths.retroarch = "/usr/bin/retroarch";
    await route.fulfill({ response: reply, json: body });
  });
  await page.goto("/settings");
  const browse = page.getByRole("button", {
    name: "Browse for RetroArch playlist",
  });
  const dialog = page.getByRole("dialog");

  await browse.focus();
  await page.keyboard.press("Enter");
  await expect(dialog).toBeVisible();
  // Focus starts on the picker itself, so Enter does not close it.
  await expect(dialog).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(dialog).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(browse).toBeFocused();

  await browse.press("Enter");
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await expect(dialog).toBeHidden();
  await expect(browse).toBeFocused();

  // From the grant prompt, as the item measured it.
  const retroarch = page.getByRole("button", {
    name: "Browse for RetroArch executable",
  });
  await retroarch.focus();
  await page.keyboard.press("Enter");
  const prompt = page.getByRole("alertdialog");
  await prompt.getByRole("button", { name: "Cancel" }).click();
  await expect(prompt).toBeHidden();
  await expect(retroarch).toBeFocused();
});

test("Browse on a file row asks to look in the folder, not at the file", async ({
  page,
}) => {
  await page.route("**/api/config", async (route) => {
    const reply = await route.fetch();
    const body = await reply.json();
    body.paths.retroarch = "/usr/bin/retroarch";
    await route.fulfill({ response: reply, json: body });
  });
  await page.goto("/settings");
  await page
    .getByRole("button", { name: "Browse for RetroArch executable" })
    .click();
  // The fixture server's real answer: outside the sandbox.
  await expect(
    page.getByRole("button", { name: "Allow /usr/bin", exact: true }),
  ).toBeVisible();
});

test("Browse on a file row opens a playlist's folder before the file exists", async ({
  page,
}) => {
  await page.goto("/settings");
  await page
    .getByRole("button", { name: "Browse for RetroArch playlist" })
    .click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("alert")).toHaveCount(0);
  await expect(
    dialog.getByRole("button", { name: "source-roms folder" }),
  ).toBeVisible();
  await expect(dialog.locator("code")).toHaveText(/data\/e2e$/);
});

test("a folder of 40,000 files draws a window of rows, and all can be reached", async ({
  page,
}) => {
  const entries = Array.from({ length: 40_000 }, (_, i) =>
    entry(`game${String(i).padStart(5, "0")}.zip`, false),
  );
  await folders(page, { entries });
  await page.goto("/settings");
  await page
    .getByRole("button", { name: "Browse for RetroArch executable" })
    .click();
  const dialog = page.getByRole("dialog");
  const first = dialog.getByRole("button", { name: "game00000.zip" });
  await expect(first).toBeVisible();
  expect(await dialog.getByRole("listitem").count()).toBeLessThan(100);

  // By keyboard: Tab walks on past what was drawn at first.
  await first.focus();
  for (let i = 1; i <= 60; i++) {
    await page.keyboard.press("Tab");
    await expect(
      dialog.getByRole("button", {
        name: `game${String(i).padStart(5, "0")}.zip`,
      }),
    ).toBeFocused();
  }

  // By scrolling, to the very last, which can be chosen.
  await dialog
    .locator("[data-testid=fs-entries]")
    .evaluate((el) => el.scrollTo(0, el.scrollHeight));
  await dialog.getByRole("button", { name: "game39999.zip" }).click();
  await expect(dialog).toBeHidden();
});

test.describe("the guide's Where step", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  async function reachWhere(page: Page) {
    await page.goto("/start");
    await page
      .getByRole("button", { name: "The best version of every game" })
      .click();
    await keepCompilations(page);
    await keepLanguages(page);
    await page.getByRole("button", { name: "Copy these" }).click();
    await expect(
      page.getByRole("button", { name: "Choose another folder" }),
    ).toBeVisible();
  }
  const heading = (page: Page) => page.getByRole("heading", { level: 1 });

  test("Cancel and Esc return focus to the opener, a choice to the heading", async ({
    page,
  }) => {
    await folders(page, { entries: [entry("roms", true)] });
    await page.route("**/api/config", async (route) => {
      if (route.request().method() === "PATCH") {
        return route.fulfill({
          status: 500,
          json: { code: "boom", detail: "it broke", fields: [] },
        });
      }
      return route.continue();
    });
    await reachWhere(page);
    const choose = page.getByRole("button", { name: "Choose another folder" });

    await choose.click();
    await page
      .getByRole("dialog")
      .getByRole("button", { name: "Cancel" })
      .click();
    await expect(page.getByRole("dialog")).toBeHidden();
    // mame-curator-1206: back to the button that opened the picker.
    await expect(choose).toBeFocused();

    await choose.click();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toBeHidden();
    await expect(choose).toBeFocused();

    await choose.click();
    await page
      .getByRole("dialog")
      .getByRole("button", { name: "Use this folder" })
      .click();
    await expect(page.getByRole("dialog")).toBeHidden();
    await expect(heading(page)).toBeFocused();
    // The refusal is said once: on the step, with no toast beside it.
    await expect(page.getByRole("alert")).toBeVisible();
    await expect(page.locator("[data-sonner-toast]")).toHaveCount(0);
  });

  test("its picker has large rows and buttons", async ({ page }) => {
    await folders(page, { entries: [entry("roms", true)] });
    await reachWhere(page);
    await page.getByRole("button", { name: "Choose another folder" }).click();
    const dialog = page.getByRole("dialog");
    for (const part of [
      dialog.getByRole("button", { name: "roms folder" }),
      dialog.getByRole("button", { name: "Use this folder" }),
      dialog.getByRole("button", { name: "Up" }),
    ]) {
      const box = (await part.boundingBox())!;
      expect(box.height).toBeGreaterThanOrEqual(48);
    }
  });
});

test.describe("mame-curator-1165: focus after a failure", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("Copy these keeps focus when the list cannot be fetched", async ({
    page,
  }) => {
    await page.goto("/start");
    await page
      .getByRole("button", { name: "The best version of every game" })
      .click();
    await keepCompilations(page);
    await keepLanguages(page);
    const copy = page.getByRole("button", { name: "Copy these" });
    await expect(copy).toBeVisible();
    await page.route("**/api/games?*", (route) =>
      route.fulfill({
        status: 500,
        json: { code: "boom", detail: "it broke", fields: [] },
      }),
    );
    await copy.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("alert")).toBeVisible();
    await expect(copy).toBeFocused();
  });
});

test("mame-curator-1165: Retry keeps focus when the Library still cannot load", async ({
  page,
}) => {
  await page.route("**/api/games?*", (route) =>
    route.fulfill({
      status: 500,
      json: { code: "boom", detail: "it broke", fields: [] },
    }),
  );
  await page.goto("/");
  const retry = page
    .getByRole("alert")
    .filter({ hasText: "Could not load" })
    .getByRole("button");
  await expect(retry).toBeVisible();
  await retry.focus();
  await page.keyboard.press("Enter");
  await expect(retry).toHaveText("Retrying…");
  await expect(retry).toHaveText("Try again", { timeout: 15_000 });
  await expect(retry).toBeFocused();
});

test("mame-curator-1169: New folder makes a folder where you are, and opens it", async ({
  page,
}) => {
  // The fixture config's destination, which git ignores.
  const dest = path.join(
    path.dirname(fileURLToPath(import.meta.url)),
    "fixtures/data/e2e/dest-roms",
  );
  const name = `new-folder-${Date.now()}`;
  try {
    await page.goto("/settings");
    await page.getByRole("button", { name: "Browse for Destination" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByRole("status")).toHaveText(/dest-roms$/);
    await dialog.getByRole("button", { name: "New folder" }).click();
    await dialog.getByLabel("Name of the new folder").fill(name);
    await dialog.getByRole("button", { name: "Make folder" }).click();
    await expect(dialog.getByRole("status")).toHaveText(
      new RegExp(`/dest-roms/${name}$`),
    );
    // An empty folder: focus goes to Up, as when one is opened from its row.
    await expect(dialog.getByRole("button", { name: "Up" })).toBeFocused();
    expect(fs.statSync(path.join(dest, name)).isDirectory()).toBe(true);
  } finally {
    fs.rmSync(path.join(dest, name), { recursive: true, force: true });
  }
});
