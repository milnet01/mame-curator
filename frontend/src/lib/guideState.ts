/**
 * mame-curator-1144 — whether the guide has opened by itself yet. Where
 * localStorage cannot read or write, the flag lives for this page's life only.
 */
export const GUIDE_SEEN_KEY = "mame-curator:guide-seen:v1";

let seenInMemory = false;

export function isGuideSeen(): boolean {
  if (seenInMemory) return true;
  try {
    return localStorage.getItem(GUIDE_SEEN_KEY) !== null;
  } catch {
    return false;
  }
}

export function markGuideSeen(): void {
  try {
    localStorage.setItem(GUIDE_SEEN_KEY, "true");
  } catch {
    seenInMemory = true;
  }
}
