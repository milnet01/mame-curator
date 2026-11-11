import { expect, test, type Page } from "@playwright/test";
import { spawn, type ChildProcess } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

/**
 * mame-curator-1149 — choosing a version, in a real browser, against a real
 * server, by keyboard, in the simple view a new user sees. Its own server and
 * port, on a game list with one parent and two clones. local-CI.sh runs
 * frontend/e2e before every push; by hand: `cd frontend && npm run build && npm
 * run e2e`.
 */
const PORT = 8092;
const BASE = `http://127.0.0.1:${PORT}`;
const projectRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../..",
);

const PARENT = "Puck Chase (World)";
const FAST = "Puck Chase (Fast)";
const JUNIOR = "Puck Chase (Junior)";

const machine = (name: string, cloneOf: string | null, description: string) =>
  `<machine name="${name}"${cloneOf ? ` cloneof="${cloneOf}" romof="${cloneOf}"` : ""}>` +
  `<description>${description}</description><year>1980</year>` +
  `<manufacturer>Namco</manufacturer>` +
  `<rom name="${name}.bin" size="16" crc="0000000${name.length}"/>` +
  `<driver status="good"/></machine>`;

const GAMES = [
  machine("puck", null, PARENT),
  machine("puckf", "puck", FAST),
  machine("puckj", "puck", JUNIOR),
  machine("solo", null, "Solo Game"),
].join("\n");

let root: string;
let server: ChildProcess;

/** Starts the server on a saved-choices file an earlier session left. */
async function startServer(saved: Record<string, string>) {
  fs.writeFileSync(
    path.join(root, "overrides.yaml"),
    `overrides: ${JSON.stringify(saved)}\n`,
  );
  server = spawn(
    path.join(projectRoot, ".venv/bin/mame-curator"),
    ["serve", "--config", "config.yaml", "--port", String(PORT)].concat(
      "--no-open-browser",
    ),
    { cwd: root, env: { ...process.env, HOME: root }, stdio: "ignore" },
  );
  for (let i = 0; i < 120; i++) {
    try {
      if ((await fetch(`${BASE}/api/setup/check`)).ok) return;
    } catch {
      // Not listening yet.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error("the version-choice server did not start");
}

test.beforeEach(async ({ page }) => {
  root = fs.mkdtempSync(path.join(os.tmpdir(), "mame-curator-versions-"));
  for (const folder of ["roms", "copied"])
    fs.mkdirSync(path.join(root, folder));
  fs.writeFileSync(
    path.join(root, "games.xml"),
    `<?xml version="1.0"?><datafile>${GAMES}</datafile>`,
  );
  fs.writeFileSync(
    path.join(root, "listxml.xml"),
    `<?xml version="1.0"?><mame>${GAMES}</mame>`,
  );
  fs.writeFileSync(
    path.join(root, "config.yaml"),
    [
      "paths:",
      `  source_roms: ${path.join(root, "roms")}`,
      `  source_dat: ${path.join(root, "games.xml")}`,
      `  dest_roms: ${path.join(root, "copied")}`,
      `  retroarch_playlist: ${path.join(root, "copied/mame.lpl")}`,
      `  listxml: ${path.join(root, "listxml.xml")}`,
      "media:",
      `  cache_dir: ${path.join(root, "media")}`,
      `  snaps_dir: ${path.join(root, "snaps")}`,
      "  sources: []",
      "updates:",
      "  check_on_startup: false",
      "  ini_check_on_startup: false",
      "",
    ].join("\n"),
  );
  await page.addInitScript(() => {
    localStorage.setItem("mame-curator:guide-seen:v1", "true");
  });
});

test.afterEach(async () => {
  const stopped = new Promise((resolve) => server.once("exit", resolve));
  server.kill();
  await stopped;
  fs.rmSync(root, { recursive: true, force: true });
});

const card = (page: Page, name: string) =>
  page.getByRole("button", { name, exact: true });
const toast = (page: Page) => page.locator("[data-sonner-toast]");
const saved = () => fs.readFileSync(path.join(root, "overrides.yaml"), "utf-8");

/** Opens `from` by keyboard, then Tabs to the version and presses Enter. */
async function chooseByKeyboard(page: Page, from: string, to: string) {
  await card(page, from).focus();
  await page.keyboard.press("Enter");
  const use = page.getByRole("button", { name: `Use ${to}`, exact: true });
  await expect(use).toBeVisible();
  for (let i = 0; i < 12; i++) {
    await page.keyboard.press("Tab");
    if (await use.evaluate((el) => el === document.activeElement)) break;
  }
  await expect(use).toBeFocused();
  await page.keyboard.press("Enter");
}

test("a clone's game moves to the chosen version, and it stays after a reload", async ({
  page,
}) => {
  await startServer({ puck: "puckf" });
  await page.goto(BASE);
  await chooseByKeyboard(page, FAST, JUNIOR);

  await expect(toast(page)).toHaveText(`Now using ${JUNIOR}.`);
  await expect(card(page, JUNIOR)).toBeVisible();
  await expect(card(page, FAST)).toHaveCount(0);
  // The game that had focus has gone, so focus follows the choice to its card.
  await expect(card(page, JUNIOR)).toBeFocused();
  expect(saved()).toContain("puck: puckj");
  expect(saved()).not.toContain("puckf:");

  await page.reload();
  await expect(card(page, JUNIOR)).toBeVisible();
  await expect(card(page, FAST)).toHaveCount(0);
});

test("the choice can be changed again and again", async ({ page }) => {
  await startServer({});
  await page.goto(BASE);
  await chooseByKeyboard(page, PARENT, FAST);
  await expect(card(page, FAST)).toBeVisible();
  await chooseByKeyboard(page, FAST, JUNIOR);
  await expect(card(page, JUNIOR)).toBeVisible();
  await chooseByKeyboard(page, JUNIOR, PARENT);
  await expect(card(page, PARENT)).toBeVisible();
  await expect(card(page, PARENT)).toBeFocused();
});

test("a game in the copy list follows the choice", async ({ page }) => {
  await startServer({ puck: "puckf" });
  await page.goto(BASE);
  await page.getByRole("button", { name: `Add ${FAST}` }).click();
  await chooseByKeyboard(page, FAST, JUNIOR);
  await expect(toast(page)).toHaveText(`Now using ${JUNIOR}.`);
  const cart = await page.evaluate(() =>
    localStorage.getItem("mame-curator:cart:v1"),
  );
  expect(JSON.parse(cart ?? "[]")).toEqual([
    { shortName: "puckf", chosenVariant: "puckj" },
  ]);
});

test("a choice saved by clone name before this fix still counts", async ({
  page,
}) => {
  await startServer({ puckf: "puckj" });
  await page.goto(BASE);
  await expect(card(page, JUNIOR)).toBeVisible();
  await expect(card(page, PARENT)).toHaveCount(0);
});

test("an old choice that cannot be used is said, and success is not", async ({
  page,
}) => {
  await startServer({ puck: "puckf", ghost: "nothing" });
  await page.goto(BASE);
  await chooseByKeyboard(page, FAST, JUNIOR);

  await expect(toast(page)).toContainText(
    "Your choice is saved, but 1 older choice",
  );
  await expect(page.getByText("Now using")).toHaveCount(0);
  await expect(card(page, JUNIOR)).toBeVisible();
});

test("a refused choice is said, success is not, and the game stays", async ({
  page,
}) => {
  await startServer({ puck: "puckf" });
  await page.route("**/api/overrides", (route) =>
    route.fulfill({
      status: 422,
      json: { code: "override_rejected", detail: "no", fields: [] },
    }),
  );
  await page.goto(BASE);
  await chooseByKeyboard(page, FAST, JUNIOR);

  await expect(toast(page)).toContainText("could not be used");
  await expect(page.getByText("Now using")).toHaveCount(0);
  await expect(card(page, FAST)).toBeVisible();
  await expect(card(page, FAST)).toBeFocused();
});

test("mame-curator-1146: the step-by-step guide changes the version", async ({
  page,
}) => {
  await startServer({ puck: "puckf" });
  await page.goto(BASE);
  await card(page, FAST).click();
  await page
    .getByRole("link", {
      name: "Fix this game's picture or version, step by step",
    })
    .click();
  await page.getByRole("button", { name: "A different version" }).click();
  await expect(
    page.getByRole("heading", { name: "Which version would you like?" }),
  ).toBeFocused();
  await page.getByRole("button", { name: JUNIOR }).click();
  await expect(
    page.getByRole("heading", { name: `Now using ${JUNIOR}.` }),
  ).toBeVisible();
  expect(saved()).toContain("puck: puckj");

  await page.getByRole("link", { name: "Back to the Library" }).click();
  await expect(card(page, JUNIOR)).toBeVisible();
  await expect(card(page, FAST)).toHaveCount(0);
});
