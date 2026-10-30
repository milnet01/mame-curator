/**
 * mame-curator-1145 §4.3: where a new user's playlist goes, inside the chosen
 * destination. Paths come from the server, so they carry its slash.
 */
export function playlistIn(dest: string): string {
  const slash = dest.includes("\\") && !dest.includes("/") ? "\\" : "/";
  return `${dest}${dest.endsWith(slash) ? "" : slash}mame.lpl`;
}
