/**
 * mame-curator-1144 — which Library the user chose: the simple one or the full
 * one. It is remembered, and the simple one is the default.
 */
export const LIBRARY_VIEW_KEY = "mame-curator:library-view:v1";

export type LibraryView = "simple" | "full";

export function readLibraryView(): LibraryView {
  try {
    return localStorage.getItem(LIBRARY_VIEW_KEY) === "full"
      ? "full"
      : "simple";
  } catch {
    return "simple";
  }
}

export function writeLibraryView(view: LibraryView): void {
  try {
    localStorage.setItem(LIBRARY_VIEW_KEY, view);
  } catch {
    /* localStorage unavailable; the choice lasts until the Library is left. */
  }
}
