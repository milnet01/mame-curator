import { useEffect, useState } from "react";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { strings } from "@/strings";

export const DEBOUNCE_MS = 200;

interface LibrarySearchBoxProps {
  search: string;
  /** Called DEBOUNCE_MS after typing stops, with what the box holds. */
  onSearch: (search: string) => void;
  /** Classes for the label-and-box wrapper. */
  className?: string;
}

/**
 * The Library's search box, in the full view's sidebar and the simple view's
 * bar. Its id, `filters-search`, is what the `/` shortcut in App.tsx focuses.
 */
export function LibrarySearchBox({
  search,
  onSearch,
  className,
}: LibrarySearchBoxProps) {
  const [draft, setDraft] = useState(search);
  // The box follows `search`, so Clear filters empties it.
  const [lastSearch, setLastSearch] = useState(search);
  // Except for a search this box sent itself: more may be typed by the time
  // it comes back.
  const [sent, setSent] = useState(search);
  if (search !== lastSearch) {
    setLastSearch(search);
    if (search !== sent) setDraft(search);
  }

  useEffect(() => {
    if (draft === search) return;
    const id = setTimeout(() => {
      setSent(draft);
      onSearch(draft);
    }, DEBOUNCE_MS);
    return () => clearTimeout(id);
    // Only a new draft re-arms the timer: the parent's callback is a new
    // function on every render and would restart it in a loop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft]);

  return (
    <div className={cn("flex flex-col", className)}>
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
  );
}
