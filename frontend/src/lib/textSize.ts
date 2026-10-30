/**
 * mame-curator-1144 — the user's text size. It lives in localStorage, not
 * UiConfig, because config loads after first paint and would flash small text.
 * Sizes are percentages of the browser's own, so they respect that setting.
 */
export const TEXT_SIZE_KEY = "mame-curator:text-size:v1";
export const TEXT_SIZES = {
  normal: "100%",
  large: "125%",
  larger: "150%",
  largest: "200%",
} as const;
export type TextSize = keyof typeof TEXT_SIZES;
export const DEFAULT_TEXT_SIZE: TextSize = "large";

const CHANGE_EVENT = "mame-curator:text-size-change";

function isTextSize(raw: string | null): raw is TextSize {
  return raw !== null && Object.keys(TEXT_SIZES).includes(raw);
}

export function readTextSize(): TextSize {
  try {
    const raw = localStorage.getItem(TEXT_SIZE_KEY);
    return isTextSize(raw) ? raw : DEFAULT_TEXT_SIZE;
  } catch {
    return DEFAULT_TEXT_SIZE;
  }
}

export function applyTextSize(size: TextSize = readTextSize()): void {
  document.documentElement.style.fontSize = TEXT_SIZES[size];
}

export function setTextSize(size: TextSize): void {
  try {
    localStorage.setItem(TEXT_SIZE_KEY, size);
  } catch {
    /* localStorage unavailable; the size still applies to this page load. */
  }
  applyTextSize(size);
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

export function subscribeTextSize(onChange: () => void): () => void {
  // "storage" fires only for a change made in another tab.
  const onStorage = (e: StorageEvent) => {
    if (e.key !== TEXT_SIZE_KEY) return;
    applyTextSize();
    onChange();
  };
  window.addEventListener(CHANGE_EVENT, onChange);
  window.addEventListener("storage", onStorage);
  return () => {
    window.removeEventListener(CHANGE_EVENT, onChange);
    window.removeEventListener("storage", onStorage);
  };
}

/** The root font size over 16, which is what rem-based content scaled by. */
export function rootFontScale(): number {
  const px = /^([\d.]+)px$/.exec(
    getComputedStyle(document.documentElement).fontSize,
  );
  return px ? Number(px[1]) / 16 : 1;
}
