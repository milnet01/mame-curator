import { useEffect, useState } from "react";
import { Link } from "react-router";
import { Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { DEBOUNCE_MS } from "@/components/library/FiltersSidebar";
import { strings } from "@/strings";

interface SimpleLibraryBarProps {
  search: string;
  onSearch: (search: string) => void;
  filtersOn: boolean;
  onClearFilters: () => void;
  shown: number;
  total: number;
  onMoreOptions: () => void;
}

/**
 * mame-curator-1144 — what the simple Library shows above the games. Hidden
 * filters are stated here, so they cannot silently shrink the list.
 */
export function SimpleLibraryBar({
  search,
  onSearch,
  filtersOn,
  onClearFilters,
  shown,
  total,
  onMoreOptions,
}: SimpleLibraryBarProps) {
  const [draft, setDraft] = useState(search);
  // The box follows filters.search, so Clear filters empties it.
  const [lastSearch, setLastSearch] = useState(search);
  if (search !== lastSearch) {
    setLastSearch(search);
    setDraft(search);
  }

  useEffect(() => {
    if (draft === search) return;
    const id = setTimeout(() => onSearch(draft), DEBOUNCE_MS);
    return () => clearTimeout(id);
    // Same shape as FiltersSidebar's debounce: only a new draft re-arms it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft]);

  return (
    <div
      data-testid="simple-library-bar"
      className="flex flex-col gap-3 border-b p-4"
    >
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex min-w-[16rem] flex-1 flex-col gap-1">
          <Label htmlFor="filters-search">
            {strings.library.filters.searchLabel}
          </Label>
          <div className="relative">
            <Search
              className="pointer-events-none absolute left-2 top-2.5 h-4 w-4 text-muted-foreground"
              aria-hidden="true"
            />
            <Input
              id="filters-search"
              type="search"
              placeholder={strings.library.filters.searchPlaceholder}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              className="pl-8"
            />
          </div>
        </div>
        <Button asChild>
          <Link to="/start">{strings.guide.simpleLibrary.startHere}</Link>
        </Button>
        <Button variant="outline" onClick={onMoreOptions}>
          {strings.guide.simpleLibrary.moreOptions}
        </Button>
      </div>
      {filtersOn && (
        <p className="flex flex-wrap items-center gap-2">
          {strings.guide.simpleLibrary.filtersOn}
          <Button variant="outline" size="sm" onClick={onClearFilters}>
            {strings.guide.simpleLibrary.clearFilters}
          </Button>
        </p>
      )}
      {total > shown && (
        <p>{strings.guide.simpleLibrary.showingFirst(shown, total)}</p>
      )}
    </div>
  );
}
