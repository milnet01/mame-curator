import { useCallback, useState } from "react";

/**
 * mame-curator-1204: remember what had focus when a dialog opened, so it can
 * be given focus back when the dialog closes.
 *
 * Radix returns focus only to a Radix trigger. The command palette, the
 * versions panel and the folder picker open from hotkeys, cards and plain
 * buttons, so without this a keyboard user is left at the top of the page.
 *
 * The opener is noted on the render where `open` turns true, or on the first
 * render when the dialog mounts open. The returned function focuses it if it
 * is still on the page, otherwise `fallback` when one is given.
 */
export function useReturnFocus(open: boolean) {
  const [wasOpen, setWasOpen] = useState(open);
  const [opener, setOpener] = useState<Element | null>(() =>
    open ? document.activeElement : null,
  );
  if (open !== wasOpen) {
    setWasOpen(open);
    if (open) setOpener(document.activeElement);
  }

  const focusOpener = useCallback(
    (fallback?: HTMLElement | null) => {
      const target =
        opener instanceof HTMLElement && opener.isConnected
          ? opener
          : (fallback ?? null);
      target?.focus();
    },
    [opener],
  );

  return focusOpener;
}
