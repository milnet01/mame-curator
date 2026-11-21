import { useEffect, useRef, useState } from "react";
import {
  readLibraryView,
  writeLibraryView,
  type LibraryView,
} from "@/lib/libraryView";

/** mame-curator-1144: the simple view shows search, games and the copy bar;
 *  the choice is remembered. mame-curator-1156: More options and Fewer
 *  options each remove the button just pressed, so focus fell to the page.
 *  It moves to the other one, through `viewButtonRef`. */
export function useLibraryViewSwitch() {
  const [view, setView] = useState<LibraryView>(readLibraryView);
  const viewButtonRef = useRef<HTMLButtonElement>(null);
  const viewChanged = useRef(false);
  const changeView = (next: LibraryView) => {
    viewChanged.current = true;
    setView(next);
    writeLibraryView(next);
  };
  useEffect(() => {
    if (!viewChanged.current) return;
    viewChanged.current = false;
    viewButtonRef.current?.focus();
  }, [view]);
  return { simple: view === "simple", changeView, viewButtonRef };
}
