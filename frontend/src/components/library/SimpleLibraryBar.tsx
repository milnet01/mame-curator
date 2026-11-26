import { Link } from "react-router";
import { Button } from "@/components/ui/button";
import { LibrarySearchBox } from "@/components/library/LibrarySearchBox";
import { strings } from "@/strings";

interface SimpleLibraryBarProps {
  search: string;
  onSearch: (search: string) => void;
  filtersOn: boolean;
  onClearFilters: () => void;
  /** Games the filters match, every page counted; null until known. */
  total: number | null;
  onMoreOptions: () => void;
  /** Takes focus when the page switches to this view. */
  viewButtonRef?: React.Ref<HTMLButtonElement>;
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
  total,
  onMoreOptions,
  viewButtonRef,
}: SimpleLibraryBarProps) {
  return (
    <div
      data-testid="simple-library-bar"
      className="flex flex-col gap-3 border-b p-4"
    >
      <div className="flex flex-wrap items-end gap-3">
        {/* mame-curator-1213: 16rem is where the box would like to start,
            not a floor; a narrower window shrinks it rather than widening
            the page. */}
        <LibrarySearchBox
          search={search}
          onSearch={onSearch}
          className="min-w-0 flex-1 basis-[16rem] gap-1"
        />
        <Button asChild>
          <Link to="/start">{strings.guide.simpleLibrary.startHere}</Link>
        </Button>
        <Button ref={viewButtonRef} variant="outline" onClick={onMoreOptions}>
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
      {total !== null && <p>{strings.guide.simpleLibrary.gameCount(total)}</p>}
    </div>
  );
}
