import { useRef } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";

import type { FsEntry } from "@/api/types";
import { cn } from "@/lib/utils";
import { strings } from "@/strings";

/** Up to here every row is on the page, as a list with nothing unusual about it. */
const DRAW_ALL_UP_TO = 300;

interface FsEntryListProps {
  entries: FsEntry[];
  emptyMessage: string;
  onOpen: (entry: FsEntry) => void;
  large?: boolean;
}

interface RowProps {
  entry: FsEntry;
  onOpen: (entry: FsEntry) => void;
  large?: boolean;
}

function Row({ entry, onOpen, large }: RowProps) {
  return (
    <button
      type="button"
      className={cn(
        "flex w-full items-center justify-between gap-2 px-3 py-2 text-left hover:bg-muted/40",
        large ? "min-h-12 text-xl" : "text-sm",
      )}
      onClick={() => onOpen(entry)}
    >
      <span className="min-w-0 [overflow-wrap:anywhere]">{entry.name}</span>
      <span
        className={cn(large ? "text-xl" : "text-xs", "text-muted-foreground")}
      >
        {entry.is_dir ? strings.settings.fsBrowserDirTag : ""}
      </span>
    </button>
  );
}

const FRAME = "max-h-72 overflow-auto rounded border border-muted";

/**
 * A folder can hold tens of thousands of files, so only the rows near the
 * window are drawn. A row's height follows its name, which wraps.
 */
function WindowedRows({
  entries,
  onOpen,
  large,
}: Omit<FsEntryListProps, "emptyMessage">) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const virtualizer = useVirtualizer({
    count: entries.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => (large ? 48 : 36),
    // Enough that the next row is there for Tab while drawing catches up.
    overscan: 30,
  });

  return (
    <div ref={scrollRef} data-testid="fs-entries" className={FRAME}>
      <ul
        className="relative w-full"
        style={{ height: virtualizer.getTotalSize() }}
      >
        {virtualizer.getVirtualItems().map((item) => {
          const entry = entries[item.index]!;
          return (
            <li
              key={entry.path}
              ref={virtualizer.measureElement}
              data-index={item.index}
              // Most rows are not on the page, so a screen reader is told.
              aria-setsize={entries.length}
              aria-posinset={item.index + 1}
              className="absolute top-0 left-0 w-full"
              style={{ transform: `translateY(${item.start}px)` }}
            >
              <Row entry={entry} onOpen={onOpen} large={large} />
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/** The picker's rows, or why there are none. */
export function FsEntryList({
  entries,
  emptyMessage,
  onOpen,
  large,
}: FsEntryListProps) {
  if (entries.length > DRAW_ALL_UP_TO) {
    return <WindowedRows entries={entries} onOpen={onOpen} large={large} />;
  }
  return (
    <ul data-testid="fs-entries" className={FRAME}>
      {entries.map((entry) => (
        <li key={entry.path}>
          <Row entry={entry} onOpen={onOpen} large={large} />
        </li>
      ))}
      {entries.length === 0 && (
        <li
          className={cn(
            "px-3 py-2 text-muted-foreground",
            large ? "text-xl" : "text-sm",
          )}
        >
          {emptyMessage}
        </li>
      )}
    </ul>
  );
}
