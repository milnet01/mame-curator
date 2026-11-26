import { useEffect, useRef } from "react";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { cn } from "@/lib/utils";
import { FacetSelect } from "./FacetSelect";
import { LibrarySearchBox } from "./LibrarySearchBox";
import { SaveSessionDialog } from "./SaveSessionDialog";
import { strings } from "@/strings";
import type { LibraryFacets, ReviewStateFilter } from "@/api/types";

/** Year-range slider extents. Earliest MAME machine is 1971; max
 *  pulled from the user's stats / DAT (FP11 § D6) — until that wiring
 *  lands, default to currentYear so the slider doesn't misclamp. */
const YEAR_MIN = 1971;
const YEAR_MAX_FALLBACK = new Date().getFullYear();

export interface FilterSidebarState {
  search: string;
  yearRange: [number, number];
  /** FP17: single-letter prefix bucket, ``'#'`` for digit-prefixed games. */
  letter: string | null;
  /** FP17: discrete genre / publisher / developer filters. */
  genre: string | null;
  publisher: string | null;
  developer: string | null;
  onlyContested: boolean;
  onlyOverridden: boolean;
  onlyChdMissing: boolean;
  onlyBiosMissing: boolean;
  /** P14 — segmented review-state filter. Default `all`. */
  reviewState: ReviewStateFilter;
}

const REVIEW_STATE_OPTIONS: {
  value: ReviewStateFilter;
  labelKey: keyof typeof strings.library.reviewState;
}[] = [
  { value: "all", labelKey: "optionAll" },
  { value: "pending", labelKey: "optionPending" },
  { value: "reviewed", labelKey: "optionReviewed" },
  { value: "skipped", labelKey: "optionSkipped" },
  { value: "needs-decision", labelKey: "optionNeedsDecision" },
];

interface FiltersSidebarProps {
  value: FilterSidebarState;
  onChange: (next: FilterSidebarState) => void;
  onSaveSession: (name: string) => void;
  /** Optional bounds passed from the library data (max year in the
   *  visible set). Falls back to currentYear when absent. */
  yearBounds?: { min: number; max: number };
  /** FP17: facet values (genres / publishers / developers / letters)
   *  drawn from /api/library/facets. Falls back to empty arrays before
   *  the hook resolves so the sidebar still renders. */
  facets?: LibraryFacets;
}

const SWITCH_KEYS = [
  "onlyContested",
  "onlyOverridden",
  "onlyChdMissing",
  "onlyBiosMissing",
] as const;

export function FiltersSidebar({
  value,
  onChange,
  onSaveSession,
  yearBounds,
  facets,
}: FiltersSidebarProps) {
  // The search box's debounce adds the search to the filters as they are
  // when it fires.
  const latestValue = useRef(value);
  useEffect(() => {
    latestValue.current = value;
  });

  const handleSwitch =
    (key: (typeof SWITCH_KEYS)[number]) => (next: boolean) => {
      onChange({ ...value, [key]: next });
    };

  const handleYearChange = (range: number[]) => {
    if (range.length !== 2) return;
    onChange({ ...value, yearRange: [range[0]!, range[1]!] });
  };

  const yearMin = yearBounds?.min ?? YEAR_MIN;
  const yearMax = yearBounds?.max ?? YEAR_MAX_FALLBACK;
  const switchLabel: Record<(typeof SWITCH_KEYS)[number], string> = {
    onlyContested: strings.library.filters.onlyContested,
    onlyOverridden: strings.library.filters.onlyOverridden,
    onlyChdMissing: strings.library.filters.onlyChdMissing,
    onlyBiosMissing: strings.library.filters.onlyBiosMissing,
  };

  return (
    <aside className="flex h-full flex-col gap-6 border-r p-4">
      <LibrarySearchBox
        search={value.search}
        onSearch={(search) => onChange({ ...latestValue.current, search })}
        className="gap-2"
      />

      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <Label htmlFor="filters-year">
            {strings.library.filters.yearRangeLabel}
          </Label>
          <span className="text-xs text-muted-foreground tabular-nums">
            {value.yearRange[0]}–{value.yearRange[1]}
          </span>
        </div>
        <Slider
          id="filters-year"
          value={value.yearRange}
          onValueChange={handleYearChange}
          min={yearMin}
          max={yearMax}
          step={1}
        />
      </div>

      {/* FP17 § C: letter prefix bucket. ``#`` = digit-prefixed games
          (1942, 005, …). Click again to clear. */}
      {facets && facets.letters.length > 0 && (
        <div className="flex flex-col gap-2">
          <Label>{strings.library.filters.letterLabel}</Label>
          <div className="flex flex-wrap gap-1">
            {facets.letters.map((l) => {
              const active = value.letter === l;
              return (
                <button
                  key={l}
                  type="button"
                  onClick={() =>
                    onChange({ ...value, letter: active ? null : l })
                  }
                  aria-pressed={active}
                  aria-label={strings.library.filters.letterAriaLabel(l)}
                  className={cn(
                    "h-7 w-7 rounded border text-xs font-medium uppercase",
                    active
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-muted bg-muted/30 hover:bg-muted",
                  )}
                >
                  {l === "#" ? "#" : l.toUpperCase()}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* FP17 § C: genre / publisher / developer Selects. Use a sentinel
          "(any)" first option that maps to null so users can clear the
          filter without a separate reset button. */}
      {facets && (
        <div className="flex flex-col gap-3">
          <FacetSelect
            id="filters-genre"
            label={strings.library.filters.genreLabel}
            value={value.genre}
            options={facets.genres}
            onChange={(v) => onChange({ ...value, genre: v })}
          />
          <FacetSelect
            id="filters-publisher"
            label={strings.library.filters.publisherLabel}
            value={value.publisher}
            options={facets.publishers}
            onChange={(v) => onChange({ ...value, publisher: v })}
          />
          <FacetSelect
            id="filters-developer"
            label={strings.library.filters.developerLabel}
            value={value.developer}
            options={facets.developers}
            onChange={(v) => onChange({ ...value, developer: v })}
          />
        </div>
      )}

      {/* P14 — segmented review-state filter (above the Only* switches). */}
      <fieldset
        className="flex flex-col gap-2"
        data-testid="filters-review-state"
      >
        <legend className="text-sm font-medium">
          {strings.library.reviewState.legendLabel}
        </legend>
        <RadioGroup
          value={value.reviewState}
          onValueChange={(next) =>
            onChange({ ...value, reviewState: next as ReviewStateFilter })
          }
          className="flex flex-wrap gap-2"
        >
          {REVIEW_STATE_OPTIONS.map((opt) => (
            <div key={opt.value} className="flex items-center gap-1.5">
              <RadioGroupItem
                id={`filters-review-state-${opt.value}`}
                value={opt.value}
              />
              <Label
                htmlFor={`filters-review-state-${opt.value}`}
                className="cursor-pointer text-sm"
              >
                {strings.library.reviewState[opt.labelKey]}
              </Label>
            </div>
          ))}
        </RadioGroup>
      </fieldset>

      <div className="flex flex-col gap-3">
        {SWITCH_KEYS.map((key) => (
          <div key={key} className="flex items-center justify-between">
            <Label htmlFor={`filters-${key}`}>{switchLabel[key]}</Label>
            <Switch
              id={`filters-${key}`}
              checked={value[key]}
              onCheckedChange={handleSwitch(key)}
            />
          </div>
        ))}
      </div>

      {/* FP15 § C: tell first-time users what a session IS before
          asking them to save one. The Save button is at the bottom of
          a long sidebar — without context it reads as cryptic jargon. */}
      <p className="text-xs text-muted-foreground">
        {strings.library.filters.sessionsExplainer}
      </p>
      <SaveSessionDialog onSave={onSaveSession} />
    </aside>
  );
}
