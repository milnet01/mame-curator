/**
 * The folder a file path sits in, by the same slash rule as `playlistIn`: paths
 * come from the server, so they carry its slash. Undefined for a bare name.
 */
export function folderOf(file: string): string | undefined {
  const slash = file.includes("/") ? "/" : "\\";
  const end = file.lastIndexOf(slash);
  if (end < 0) return undefined;
  const folder = file.slice(0, end);
  // The top of a drive keeps its slash: "/" and "C:\", never "" and "C:".
  return folder === "" || folder.endsWith(":") ? `${folder}${slash}` : folder;
}
