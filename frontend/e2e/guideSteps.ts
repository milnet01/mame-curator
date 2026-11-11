import type { Page } from "@playwright/test";

// The guide's two steps after the group choice, shared by every spec that
// walks past them (mame-curator-1222). The fixture keeps both.

/** mame-curator-1216: the step after the group choice; the fixture's answer is "keep". */
export async function keepCompilations(page: Page) {
  await page.getByRole("button", { name: /^No, keep them/ }).click();
}

/** mame-curator-1217: the step after compilations; the fixture keeps every language. */
export async function keepLanguages(page: Page) {
  await page.getByRole("button", { name: /^Keep every language/ }).click();
}
