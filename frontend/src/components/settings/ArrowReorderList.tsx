import { useState, type KeyboardEvent, type ReactNode } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";

import { cn } from "@/lib/utils";

export interface ArrowReorderListProps {
  /** Accessible name for the list (e.g. "Region priority"). */
  ariaLabel: string;
  /** Current items, rendered top-to-bottom in priority order. */
  items: string[];
  /** Called with the next list whenever an item is reordered. */
  onChange: (next: string[]) => void;
  /**
   * P10 chunk 10: optionally render rich row content in place of the plain
   * item label (e.g. a media source's status dot + Configure button).
   * Replaces ONLY the label span — the arrow buttons and the row-level
   * ArrowUp/ArrowDown reorder handler are unchanged. Interactive controls
   * inside `renderItem` should `stopPropagation` on keydown so they don't
   * also trigger a reorder. Defaults to the plain item string.
   */
  renderItem?: (item: string) => ReactNode;
}

function swap(arr: string[], from: number, to: number): string[] {
  const next = arr.slice();
  [next[from], next[to]] = [next[to], next[from]];
  return next;
}

// `role="list"`, not a listbox: rows are moved by per-row controls, and the
// aria-live region announces each move.
export function ArrowReorderList({
  ariaLabel,
  items,
  onChange,
  renderItem,
}: ArrowReorderListProps) {
  const [announcement, setAnnouncement] = useState("");

  const move = (from: number, to: number) => {
    if (to < 0 || to >= items.length) return;
    const moved = items[from];
    onChange(swap(items, from, to));
    // FP13 § D2: announce moves via an aria-live region so screen-reader
    // users hear that the action took effect. Without this the keyboard
    // reorder is silent to AT — failure mode flagged in FP12 closing review.
    setAnnouncement(`Moved ${moved} to position ${to + 1} of ${items.length}.`);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLLIElement>, index: number) => {
    if (event.key === "ArrowUp") {
      event.preventDefault();
      move(index, index - 1);
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      move(index, index + 1);
    }
  };

  return (
    <>
      <ul role="list" aria-label={ariaLabel} className="flex flex-col gap-1">
        {/* `key={item}` keeps focus on a row as it moves, so items must be
            unique. The server checks neither caller's list: Settings →
            Media's source toggle adds a name only when it is absent, and
            Picker's region_priority is as config.yaml spells it. */}
        {items.map((item, i) => {
          const isFirst = i === 0;
          const isLast = i === items.length - 1;
          return (
            <li
              key={item}
              tabIndex={0}
              onKeyDown={(e) => onKeyDown(e, i)}
              className="flex items-center justify-between gap-2 rounded border border-input bg-muted/30 px-2 py-1 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {renderItem ? renderItem(item) : <span>{item}</span>}
              <div className="flex gap-1">
                <button
                  type="button"
                  aria-label={`Move ${item} up`}
                  disabled={isFirst}
                  onClick={() => move(i, i - 1)}
                  className={cn(
                    "rounded p-0.5 hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                    isFirst && "opacity-40",
                  )}
                >
                  <ChevronUp size={14} aria-hidden="true" />
                </button>
                <button
                  type="button"
                  aria-label={`Move ${item} down`}
                  disabled={isLast}
                  onClick={() => move(i, i + 1)}
                  className={cn(
                    "rounded p-0.5 hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                    isLast && "opacity-40",
                  )}
                >
                  <ChevronDown size={14} aria-hidden="true" />
                </button>
              </div>
            </li>
          );
        })}
      </ul>
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        {announcement}
      </div>
    </>
  );
}
