import { expect, test } from "@playwright/test";

/**
 * mame-curator-1144 — a page that cannot load says so and offers a way
 * forward, and a keyboard user keeps their place when a retry fails too. Run
 * by hand: no gate runs frontend/e2e.
 */
test("Settings says it failed, and Try again keeps focus until it works", async ({
  page,
}) => {
  let answer: "fail" | "pass" = "fail";
  await page.route("**/api/config", async (route) => {
    if (answer === "pass") return route.continue();
    await route.fulfill({
      status: 500,
      json: { code: "boom", detail: "it broke", fields: [] },
    });
  });

  await page.goto("/settings");
  const alert = page.getByRole("alert");
  await expect(alert).toContainText("Could not load your settings.");
  await expect(page.getByText("Loading settings")).toHaveCount(0);

  const tryAgain = page.getByRole("button", { name: "Try again" });
  await tryAgain.focus();
  await page.keyboard.press("Enter");
  await expect(tryAgain).toBeFocused();
  await expect(alert).toContainText("Could not load your settings.");

  answer = "pass";
  await page.keyboard.press("Enter");
  await expect(alert).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
});

test("A failed session delete says so after its dialog has closed", async ({
  page,
}) => {
  await page.route("**/api/sessions", (route) =>
    route.fulfill({
      json: {
        active: null,
        sessions: {
          fighters: {
            include_genres: [],
            include_publishers: [],
            include_developers: [],
            include_year_range: null,
          },
        },
      },
    }),
  );
  await page.route("**/api/sessions/fighters", (route) =>
    route.fulfill({
      status: 500,
      json: { code: "boom", detail: "it broke", fields: [] },
    }),
  );

  await page.goto("/sessions");
  await page.getByRole("button", { name: "Delete fighters" }).click();
  await page
    .getByRole("alertdialog")
    .getByRole("button", { name: /fighters/ })
    .click();

  await expect(page.getByRole("alertdialog")).toHaveCount(0);
  await expect(page.getByRole("alert")).toContainText(
    '"fighters" could not be deleted.',
  );
  await expect(page.getByRole("alert")).toContainText("it broke");
});
