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
import { strings } from '@/strings'

const DEBOUNCE_MS = 200

/** Year-range slider extents. Earliest MAME machine is 1971; max
 *  pulled from the user's stats / DAT (FP11 § D6) — until that wiring
 *  lands, default to currentYear so the slider doesn't misclamp. */
const YEAR_MIN = 1971
const YEAR_MAX_FALLBACK = new Date().getFullYear()

export interface FilterSidebarState {
  search: string
  yearRange: [number, number]
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
