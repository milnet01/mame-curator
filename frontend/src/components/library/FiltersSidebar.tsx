import { useEffect, useRef, useState } from 'react'
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

const DEBOUNCE_MS = 200

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
}

const SWITCHES: Array<{
  key: keyof FilterSidebarState
  label: string
}> = [
  { key: 'onlyContested', label: 'Only contested picks' },
  { key: 'onlyOverridden', label: 'Only manual overrides' },
  { key: 'onlyChdMissing', label: 'Only CHD missing' },
  { key: 'onlyBiosMissing', label: 'Only BIOS missing' },
]

export function FiltersSidebar({
  value,
  onChange,
  onSaveSession,
}: FiltersSidebarProps) {
  const [searchDraft, setSearchDraft] = useState(value.search)
  const [saveDialogOpen, setSaveDialogOpen] = useState(false)
  const [sessionName, setSessionName] = useState('')
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (searchDraft === value.search) return
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      onChange({ ...value, search: searchDraft })
    }, DEBOUNCE_MS)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
    // We intentionally watch only the local draft — the parent's `value`
    // identity changes on every dispatch and would otherwise re-arm the
    // timer in a loop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchDraft])

  const handleSwitch = (key: keyof FilterSidebarState) => (next: boolean) => {
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

  return (
    <aside className="flex h-full flex-col gap-6 border-r p-4">
      <div className="flex flex-col gap-2">
        <Label htmlFor="filters-search">Search</Label>
        <div className="relative">
          <Search
            className="pointer-events-none absolute left-2 top-2.5 h-4 w-4 text-muted-foreground"
            aria-hidden="true"
          />
          <Input
            id="filters-search"
            type="search"
            placeholder="Search games…"
            value={searchDraft}
            onChange={(e) => setSearchDraft(e.target.value)}
            className="pl-8"
          />
        </div>
      </div>

      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <Label htmlFor="filters-year">Year range</Label>
          <span className="text-xs text-muted-foreground tabular-nums">
            {value.yearRange[0]}–{value.yearRange[1]}
          </span>
        </div>
        <Slider
          id="filters-year"
          value={value.yearRange}
          onValueChange={handleYearChange}
          min={1975}
          max={2025}
          step={1}
        />
      </div>

      <div className="flex flex-col gap-3">
        {SWITCHES.map(({ key, label }) => (
          <div key={key} className="flex items-center justify-between">
            <Label htmlFor={`filters-${key}`}>{label}</Label>
            <Switch
              id={`filters-${key}`}
              checked={value[key] as boolean}
              onCheckedChange={handleSwitch(key)}
            />
          </div>
        ))}
      </div>

      <Dialog open={saveDialogOpen} onOpenChange={setSaveDialogOpen}>
        <DialogTrigger asChild>
          <Button variant="outline">Save as session</Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Save as session</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-2">
            <Label htmlFor="session-name">Session name</Label>
            <Input
              id="session-name"
              value={sessionName}
              onChange={(e) => setSessionName(e.target.value)}
              autoFocus
            />
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setSaveDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSave}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </aside>
  )
}
