import type { PictureChoice } from "@/api/types";

/**
 * mame-curator-1146 §4.5: a card's image address. With a stored picture
 * choice it names the choice, so a new choice is a new address the browser
 * fetches instead of showing the image it cached for 30 days. Clearing
 * returns to the plain address, which holds the usual picture.
 */
export function pictureSrc(card: {
  short_name: string;
  picture: PictureChoice | null;
}): string {
  const base = `/media/${encodeURIComponent(card.short_name)}/boxart`;
  if (card.picture === null) return base;
  const { source, kind } = card.picture;
  return `${base}?v=${encodeURIComponent(`${source}.${kind}`)}`;
}
