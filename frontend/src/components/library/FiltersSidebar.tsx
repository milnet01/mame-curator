import { useEffect, useState } from 'react'
import { Search } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Slider } from '@/components/ui/slider'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { cn } from '@/lib/utils'
import { strings } from '@/strings'
import type { LibraryFacets } from '@/api/types'

const DEBOUNCE_MS = 200

/** Year-range slider extents. Earliest MAME machine is 1971; max
 *  pulled from the user's stats / DAT (FP11 § D6) — until that wiring
 *  lands, default to currentYear so the slider doesn't misclamp. */
const YEAR_MIN = 1971
const YEAR_MAX_FALLBACK = new Date().getFullYear()

export interface FilterSidebarState {
  search: string
  yearRange: [number, number]
  /** FP17: single-letter prefix bucket, ``'#'`` for digit-prefixed games. */
  letter: string | null
  /** FP17: discrete genre / publisher / developer filters. */
  genre: string | null
  publisher: string | null
  developer: string | null
  onlyContested: boolean
  onlyOverridden: boolean
  onlyChdMissing: boolean
  onlyBiosMissing: boolean
}

interface FiltersSidebarProps {
  value: FilterSidebarState
  onChange: (next: FilterSidebarState) => void
  onSaveSession: (name: string) => void
  /** Optional bounds passed from the library data (max year in the
   *  visible set). Falls back to currentYear when absent. */
  yearBounds?: { min: number; max: number }
  /** FP17: facet values (genres / publishers / developers / letters)
   *  drawn from /api/library/facets. Falls back to empty arrays before
   *  the hook resolves so the sidebar still renders. */
  facets?: LibraryFacets
}

const SWITCH_KEYS = [
  'onlyContested',
  'onlyOverridden',
  'onlyChdMissing',
  'onlyBiosMissing',
] as const

export function FiltersSidebar({
  value,
  onChange,
  onSaveSession,
  yearBounds,
  facets,
}: FiltersSidebarProps) {
  const [searchDraft, setSearchDraft] = useState(value.search)
  const [saveDialogOpen, setSaveDialogOpen] = useState(false)
  const [sessionName, setSessionName] = useState('')

  // FP11 § D7: canonical debounce — single useEffect, single timer,
  // single cleanup. The prior implementation used a useRef + manual
  // double-clear; the React-canonical shape (timer is closed-over by
  // the cleanup) is shorter and equivalent.
  useEffect(() => {
    if (searchDraft === value.search) return
    const id = setTimeout(() => {
      onChange({ ...value, search: searchDraft })
    }, DEBOUNCE_MS)
    return () => clearTimeout(id)
    // Watching only `searchDraft` is intentional — the parent `value`
    // identity churns on every dispatch and would re-arm the timer
    // in a loop. The `searchDraft === value.search` short-circuit
    // above handles the steady-state case.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchDraft])

  const handleSwitch =
    (key: (typeof SWITCH_KEYS)[number]) => (next: boolean) => {
      onChange({ ...value, [key]: next })
    }

  const handleYearChange = (range: number[]) => {
    if (range.length !== 2) return
    onChange({ ...value, yearRange: [range[0]!, range[1]!] })
  }

  const handleSave = () => {
    if (!sessionName.trim()) return
    onSaveSession(sessionName.trim())
    setSessionName('')
    setSaveDialogOpen(false)
  }

  const yearMin = yearBounds?.min ?? YEAR_MIN
  const yearMax = yearBounds?.max ?? YEAR_MAX_FALLBACK
  const switchLabel: Record<(typeof SWITCH_KEYS)[number], string> = {
    onlyContested: strings.library.filters.onlyContested,
    onlyOverridden: strings.library.filters.onlyOverridden,
    onlyChdMissing: strings.library.filters.onlyChdMissing,
    onlyBiosMissing: strings.library.filters.onlyBiosMissing,
  }

  return (
    <aside className="flex h-full flex-col gap-6 border-r p-4">
      <div className="flex flex-col gap-2">
        <Label htmlFor="filters-search">{strings.library.filters.searchLabel}</Label>
        <div className="relative">
          <Search
            className="pointer-events-none absolute left-2 top-2.5 h-4 w-4 text-muted-foreground"
            aria-hidden="true"
          />
          <Input
            id="filters-search"
            type="search"
            placeholder={strings.library.filters.searchPlaceholder}
            value={searchDraft}
            onChange={(e) => setSearchDraft(e.target.value)}
            className="pl-8"
          />
        </div>
      </div>

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
              const active = value.letter === l
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
                    'h-7 w-7 rounded border text-xs font-medium uppercase',
                    active
                      ? 'border-primary bg-primary text-primary-foreground'
                      : 'border-muted bg-muted/30 hover:bg-muted',
                  )}
                >
                  {l === '#' ? '#' : l.toUpperCase()}
                </button>
              )
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
      <Dialog open={saveDialogOpen} onOpenChange={setSaveDialogOpen}>
        <DialogTrigger asChild>
          <Button variant="outline">{strings.library.filters.saveAsSession}</Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{strings.library.filters.saveAsSession}</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-2">
            <Label htmlFor="session-name">
              {strings.library.filters.sessionNameLabel}
            </Label>
            <Input
              id="session-name"
              value={sessionName}
              onChange={(e) => setSessionName(e.target.value)}
              autoFocus
            />
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setSaveDialogOpen(false)}>
              {strings.common.cancel}
            </Button>
            <Button onClick={handleSave}>{strings.common.save}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </aside>
  )
}

/** FP17 § C: facet Select with a sentinel "(any)" first option that
 *  maps to null. Renders nothing when the options list is empty so the
 *  sidebar doesn't show a useless empty dropdown. */
function FacetSelect({
  id,
  label,
  value,
  options,
  onChange,
}: {
  id: string
  label: string
  value: string | null
  options: readonly string[]
  onChange: (next: string | null) => void
}) {
  if (options.length === 0) return null
  const ANY = '__any__'
  return (
    <div className="flex flex-col gap-1">
      <Label htmlFor={id}>{label}</Label>
      <Select
        value={value ?? ANY}
        onValueChange={(v) => onChange(v === ANY ? null : v)}
      >
        <SelectTrigger id={id} aria-label={label}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ANY}>{strings.library.filters.anyOption}</SelectItem>
          {options.map((o) => (
            <SelectItem key={o} value={o}>
              {o}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
