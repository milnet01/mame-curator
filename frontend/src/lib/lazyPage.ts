/** Set while a reload for a missing page file is under way. */
export const PAGE_RELOAD_KEY = "mame-curator:page-file-reload:v1";

/**
 * mame-curator-1233: wraps a page's `import()` for React.lazy. After an
 * in-app update, an open tab asks for page files the update replaced, and
 * React.lazy keeps that failure for good, so Retry cannot help. The first
 * failure reloads the page, which fetches the new files. A failure after that
 * reload goes to the error panel, so a missing file cannot reload for ever;
 * so does any failure when storage is blocked, as nothing could stop a loop.
 */
export function reloadOnceIfMissing<T>(
  load: () => Promise<T>,
  reload: () => void = () => window.location.reload(),
): () => Promise<T> {
  return () =>
    load().then(
      (page) => {
        try {
          sessionStorage.removeItem(PAGE_RELOAD_KEY);
        } catch {
          /* blocked storage: nothing was set */
        }
        return page;
      },
      (error: unknown) => {
        if (!startReload()) throw error;
        reload();
        return new Promise<T>(() => {}); // The reload replaces this page.
      },
    );
}

/** True when this tab has not just reloaded for a missing file. */
function startReload(): boolean {
  try {
    if (sessionStorage.getItem(PAGE_RELOAD_KEY) !== null) return false;
    sessionStorage.setItem(PAGE_RELOAD_KEY, "1");
    return true;
  } catch {
    return false;
  }
}
