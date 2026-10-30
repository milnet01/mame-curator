import { Link } from "react-router";
import { LayoutSwitcher } from "@/components/library/LayoutSwitcher";
import { ThemeSwitcher } from "@/components/library/ThemeSwitcher";
import { WALKTHROUGH_KEY } from "@/pages/libraryPageHelpers";
import { strings } from "@/strings";
import type { GameCard, LayoutName, ThemeName } from "@/api/types";

interface LibraryFullHeaderProps {
  activeSession: string | null;
  cards: GameCard[];
  reviewEntries: Record<string, unknown>;
  walkthrough: boolean;
  onWalkthroughChange: (next: boolean) => void;
  layout: LayoutName;
  onLayoutChange: (next: LayoutName) => void;
  theme: ThemeName;
  onThemeChange: (next: ThemeName) => void;
  onFewerOptions: () => void;
}

/** The full Library's top bar; the simple view has SimpleLibraryBar instead. */
export function LibraryFullHeader({
  activeSession,
  cards,
  reviewEntries,
  walkthrough,
  onWalkthroughChange,
  layout,
  onLayoutChange,
  theme,
  onThemeChange,
  onFewerOptions,
}: LibraryFullHeaderProps) {
  return (
    <header className="flex flex-wrap items-center justify-end gap-2 border-b px-4 py-2">
      <button
        type="button"
        onClick={onFewerOptions}
        className="rounded border bg-muted/50 px-2 py-1 text-xs hover:bg-muted"
      >
        {strings.guide.simpleLibrary.fewerOptions}
      </button>
      <Link
        to="/sessions"
        className="rounded border bg-muted/50 px-2 py-1 text-xs text-muted-foreground hover:bg-muted"
        title={
          activeSession
            ? strings.library.activeSessionTitle(activeSession)
            : strings.library.noActiveSessionTitle
        }
      >
        {activeSession
          ? strings.library.activeSessionPill(activeSession)
          : strings.library.noActiveSessionPill}
      </Link>
      {/* P14 — progress chip + walkthrough toggle. */}
      {(() => {
        const totalSlice = cards.length;
        const handled = cards.reduce(
          (n, c) => n + (c.short_name in reviewEntries ? 1 : 0),
          0,
        );
        const pct =
          totalSlice === 0 ? "0" : ((handled / totalSlice) * 100).toFixed(1);
        return (
          <span
            data-testid="library-progress-chip"
            className="rounded border bg-muted/50 px-2 py-1 text-xs text-muted-foreground"
          >
            {strings.library.progressChip(handled, totalSlice, pct)}
          </span>
        );
      })()}
      <label className="flex items-center gap-1 rounded border bg-muted/50 px-2 py-1 text-xs text-muted-foreground">
        <input
          type="checkbox"
          data-testid="library-walkthrough-toggle"
          checked={walkthrough}
          onChange={(e) => {
            onWalkthroughChange(e.target.checked);
            try {
              localStorage.setItem(WALKTHROUGH_KEY, String(e.target.checked));
            } catch {
              /* localStorage unavailable; in-memory state still updates. */
            }
          }}
        />
        {strings.library.walkthroughToggle}
      </label>
      <LayoutSwitcher value={layout} onChange={onLayoutChange} />
      <ThemeSwitcher value={theme} onChange={onThemeChange} />
    </header>
  );
}
