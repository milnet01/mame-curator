import type { ReactNode } from "react";
import { LibraryErrorPanel } from "@/components/library/LibraryErrorPanel";
import { type useGamesList } from "@/hooks/useGames";
import { strings } from "@/strings";

/** The games list's error panel or loading line, or, once games have
 *  loaded, `children` (the grid). */
export function LibraryGamesState({
  games,
  children,
}: {
  games: ReturnType<typeof useGamesList>;
  children: ReactNode;
}) {
  // FP20-I: query failure surfaces as an inline alert with a
  // Retry affordance; the FP20-G global toast already flashed
  // at error time, but it dismisses — this panel keeps the
  // failure visible until the user retries.
  //
  // FP26-V: keep the panel mounted while a refetch FROM an
  // errored state is in flight. React Query v5 resets
  // `isError` to false during refetch (so the prior `{games.
  // isError ? ...}` ternary unmounted the panel mid-retry —
  // FP25-H's `disabled={isFetching}` / "Retrying…" affordance
  // never reached the user's screen). `errorUpdatedAt >
  // dataUpdatedAt` tells us the last completed settle was an
  // error, so we sticky-render the panel through the refetch
  // window; once the refetch resolves successfully,
  // dataUpdatedAt moves ahead and the grid takes over.
  const lastSettleWasError =
    (games.errorUpdatedAt ?? 0) > (games.dataUpdatedAt ?? 0);
  if (games.isError || (games.isFetching && lastSettleWasError)) {
    return (
      <LibraryErrorPanel
        onRetry={() => games.refetch()}
        isFetching={games.isFetching}
      />
    );
  }
  // mame-curator-1102: no data yet for this query — `cards` is the `[]`
  // default, so the grid would claim nothing matched. isPending, not
  // isFetching: a background refetch of data already on screen must not
  // blank the grid.
  if (games.isPending) {
    return (
      <div
        role="status"
        aria-live="polite"
        className="p-4 text-sm text-muted-foreground"
      >
        {strings.loading.library}
      </div>
    );
  }
  return children;
}
