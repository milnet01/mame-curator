import { expect, test, type Page } from "@playwright/test";
import { spawn, type ChildProcess } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

/**
 * mame-curator-1145 INV-10, INV-12, INV-14 — a brand-new user, in a real
 * browser, against a real server. Run by hand: no gate runs frontend/e2e, so
 * `cd frontend && npm run build && npm run e2e`.
 *
 * This starts its own server, with an empty home and no config, so the server
 * writes its own starter config exactly as on a first run. It has its own
 * port, so its own origin, so the browser holds none of the guide's keys.
 */
const PORT = 8091;
const BASE = `http://127.0.0.1:${PORT}`;
const projectRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../..",
);
const dat = path.join(projectRoot, "tests/parser/fixtures/mini.dat.xml");

let root: string;
let server: ChildProcess;

async function serverIsUp() {
  for (let i = 0; i < 120; i++) {
    try {
      const reply = await fetch(`${BASE}/api/setup/check`);
      if (reply.ok) return;
    } catch {
      // Not listening yet.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error("the wizard's server did not start");
}

test.beforeAll(async () => {
  root = fs.mkdtempSync(path.join(os.tmpdir(), "mame-curator-wizard-"));
  const home = path.join(root, "home");
  fs.mkdirSync(path.join(home, "copied"), { recursive: true });
  // Outside the home folder, so reaching them walks the picker's grant.
  fs.mkdirSync(path.join(root, "games"));
  fs.mkdirSync(path.join(root, "lists"));
  fs.copyFileSync(dat, path.join(root, "lists", "mini.dat.xml"));
  fs.writeFileSync(path.join(root, "lists", "notes.xml"), "<not a game list");

  server = spawn(
    path.join(projectRoot, ".venv/bin/mame-curator"),
    ["serve", "--port", String(PORT), "--no-open-browser"],
    {
      cwd: root,
      env: {
        ...process.env,
        HOME: home,
        XDG_CONFIG_HOME: path.join(home, ".config"),
        XDG_DATA_HOME: path.join(home, ".local/share"),
      },
      stdio: "ignore",
    },
  );
  await serverIsUp();
});

test.afterAll(() => {
  server?.kill();
  fs.rmSync(root, { recursive: true, force: true });
});

const heading = (page: Page, name: string) =>
  page.getByRole("heading", { name, exact: true });

async function expectFocusedHeading(page: Page, name: string) {
  await expect(heading(page, name)).toBeVisible();
  await expect(heading(page, name)).toBeFocused();
}

/** Opens each folder on `route` in turn, from the picker's current folder. */
async function openFolders(page: Page, route: string[]) {
  const dialog = page.getByRole("dialog");
  for (const name of route) {
    await dialog
      .getByRole("button", { name: `${name} folder`, exact: true })
      .click();
  }
}

test("a new user reaches a Library with games, in three questions", async ({
  page,
}) => {
  test.setTimeout(120_000);
  // From the filesystem's top, as the picker's drive button starts there.
  const toRoot = root.split(path.sep).filter(Boolean);

  await page.goto(`${BASE}/`);
  await expect(page).toHaveURL(/\/start$/);
  await expectFocusedHeading(page, "Where are your MAME games?");
  await expect(page.getByText("Step 1 of 3")).toBeVisible();

  // Step 1: the games are outside home, so the picker asks, then stays open.
  await page.getByRole("button", { name: "Choose a folder" }).click();
  const dialog = page.getByRole("dialog");
  // INV-12: the whole picker fits the window, and shows only what a new user
  // needs: not the app's own folders, and not hidden ones.
  await expect(
    dialog.getByRole("heading", { name: "Choose a folder" }),
  ).toBeInViewport();
  await expect(
    dialog.getByRole("button", { name: "Use this folder" }),
  ).toBeInViewport();
  await expect(dialog.getByRole("button", { name: "Cancel" })).toBeInViewport();
  await expect(
    dialog.getByRole("button", { name: /mame-curator/ }),
  ).toHaveCount(0);
  await expect(
    dialog.getByRole("button", { name: ".config folder" }),
  ).toHaveCount(0);
  await expect(
    dialog.getByRole("button", { name: "copied folder" }),
  ).toBeVisible();
  await dialog.getByRole("button", { name: "/", exact: true }).click();
  await page.getByRole("button", { name: "Allow /" }).click();
  await expect(dialog.getByText("Choose a folder")).toBeVisible();
  await openFolders(page, [...toRoot, "games"]);
  await dialog.getByRole("button", { name: "Use this folder" }).click();
  await expectFocusedHeading(page, "Use this folder for your games?");
  await expect(
    page.getByRole("status").filter({ hasText: path.join(root, "games") }),
  ).toBeVisible();

  // A second choice keeps the heading, and focus still comes back to it.
  await page.getByRole("button", { name: "Choose another folder" }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Use this folder" })
    .click();
  await expect(page.getByRole("dialog")).toBeHidden();
  await expectFocusedHeading(page, "Use this folder for your games?");

  // Cancelling keeps the choice, and focus does not fall off the page.
  await page.getByRole("button", { name: "Choose another folder" }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Cancel" })
    .click();
  await expect(page.getByRole("dialog")).toBeHidden();
  await expectFocusedHeading(page, "Use this folder for your games?");

  // Step 2: first a file that is not a game list.
  await page.getByRole("button", { name: "Yes, use this folder" }).click();
  await expectFocusedHeading(page, "Where is your game list?");
  await page.getByRole("button", { name: "Choose a file" }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "/", exact: true })
    .click();
  await openFolders(page, [...toRoot, "lists"]);
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "notes.xml" })
    .click();
  await expectFocusedHeading(page, "Use this game list?");
  await page.getByRole("button", { name: "Yes, use this file" }).click();

  // Step 3: the save finds the file is bad, and returns to step 2.
  await expectFocusedHeading(page, "Where should copied games go?");
  await page.getByRole("button", { name: "Choose a folder" }).click();
  await openFolders(page, ["copied"]);
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Use this folder" })
    .click();
  await expectFocusedHeading(page, "Copy games to this folder?");
  await page.getByRole("button", { name: "Yes, finish setup" }).click();
  await expectFocusedHeading(page, "Where is your game list?");
  await expect(page.getByRole("alert")).toHaveText(
    "That file could not be read as a game list. Please choose another.",
  );

  // The right file: the games load with no restart, and the guide begins.
  await page.getByRole("button", { name: "Choose a file" }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "/", exact: true })
    .click();
  await openFolders(page, [...toRoot, "lists"]);
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "mini.dat.xml" })
    .click();
  await page.getByRole("button", { name: "Yes, use this file" }).click();
  await expectFocusedHeading(page, "Copy games to this folder?");
  await page.getByRole("button", { name: "Yes, finish setup" }).click();
  await expectFocusedHeading(page, "Which games would you like?");

  // The guide finds games, and the Library shows them.
  await page
    .getByRole("button", { name: "The best version of every game" })
    .click();
  await expect(
    page.getByRole("heading", { name: /^This finds \d/ }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Look around on my own" }).click();
  await expect(page).toHaveURL(`${BASE}/`);
  await expect(
    page
      .getByTestId("library-grid")
      .getByText(/Pac-Man/)
      .first(),
  ).toBeVisible();

  // The same four keys `mame-curator setup` writes.
  const reply = await (await fetch(`${BASE}/api/config`)).json();
  expect(reply.paths).toMatchObject({
    source_roms: path.join(root, "games"),
    source_dat: path.join(root, "lists", "mini.dat.xml"),
    dest_roms: path.join(root, "home", "copied"),
    retroarch_playlist: path.join(root, "home", "copied", "mame.lpl"),
  });
});
