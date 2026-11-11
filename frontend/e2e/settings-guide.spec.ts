import { expect, test } from "@playwright/test";
import { spawn, type ChildProcess } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

/**
 * mame-curator-1147 — the Settings guide, in a real browser, against a real
 * server that writes its own config file. Its own server and port, so the
 * shared fixture config is never written. local-CI.sh runs frontend/e2e before
 * every push; by hand: `cd frontend && npm run build && npm run e2e`.
 */
const PORT = 8093;
const BASE = `http://127.0.0.1:${PORT}`;
const projectRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../..",
);

let root: string;
let server: ChildProcess;

test.beforeEach(async ({ page }) => {
  root = fs.mkdtempSync(path.join(os.tmpdir(), "mame-curator-settings-"));
  for (const folder of ["roms", "copied"])
    fs.mkdirSync(path.join(root, folder));
  fs.copyFileSync(
    path.join(projectRoot, "tests/parser/fixtures/mini.dat.xml"),
    path.join(root, "games.xml"),
  );
  fs.writeFileSync(
    path.join(root, "config.yaml"),
    [
      "paths:",
      `  source_roms: ${path.join(root, "roms")}`,
      `  source_dat: ${path.join(root, "games.xml")}`,
      `  dest_roms: ${path.join(root, "copied")}`,
      `  retroarch_playlist: ${path.join(root, "copied/mame.lpl")}`,
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
  server = spawn(
    path.join(projectRoot, ".venv/bin/mame-curator"),
    ["serve", "--config", "config.yaml", "--port", String(PORT)].concat(
      "--no-open-browser",
    ),
    { cwd: root, env: { ...process.env, HOME: root }, stdio: "ignore" },
  );
  for (let i = 0; i < 120; i++) {
    try {
      if ((await fetch(`${BASE}/api/setup/check`)).ok) break;
    } catch {
      // Not listening yet.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
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

test("a kind of game is let back in, one question at a time", async ({
  page,
}) => {
  await page.goto(`${BASE}/settings`);
  await page
    .getByRole("link", { name: "Change a setting, step by step" })
    .click();
  await expect(
    page.getByRole("heading", { name: "What would you like to change?" }),
  ).toBeFocused();
  await page
    .getByRole("button", { name: "Which kinds of games to leave out" })
    .click();
  await page.getByRole("button", { name: /^Games for adults/ }).click();
  await expect(
    page.getByRole("heading", { name: "Leave out games for adults?" }),
  ).toBeFocused();
  await page.getByRole("button", { name: "No, keep them in" }).click();

  await expect(
    page.getByRole("heading", {
      name: "Games for adults are now in your library.",
    }),
  ).toBeFocused();
  const saved = fs.readFileSync(path.join(root, "config.yaml"), "utf-8");
  expect(saved).toContain("drop_mature: false");

  await page.getByRole("button", { name: "Change something else" }).click();
  await page.getByRole("link", { name: "Back to Settings" }).click();
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
});
