import type { PictureChoice } from "@/api/types";

/**
 * mame-curator-1146 §4.5: a card's image address. With a stored picture
 * choice it names the choice, so a new choice is a new address the browser
 * fetches instead of showing the image it cached for 30 days. Clearing
 * returns to the plain address, which holds the usual picture.
 *
 * mame-curator-1143: `look` counts fresh looks that found a picture
 * (`usePictureLook`); a new count is a new address, so a card that showed
 * no picture asks again.
 */
export function pictureSrc(
  card: {
    short_name: string;
    picture: PictureChoice | null;
  },
  look = 0,
): string {
  const base = `/media/${encodeURIComponent(card.short_name)}/boxart`;
  const query: string[] = [];
  if (card.picture !== null) {
    const { source, kind } = card.picture;
    query.push(`v=${encodeURIComponent(`${source}.${kind}`)}`);
  }
  if (look > 0) query.push(`r=${look}`);
  return query.length === 0 ? base : `${base}?${query.join("&")}`;
}
