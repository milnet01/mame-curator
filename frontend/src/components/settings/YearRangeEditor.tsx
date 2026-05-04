import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'

export interface YearRangeEditorProps {
  /** Lower-bound year filter; null disables the filter. */
  before: number | null
  /** Upper-bound year filter; null disables the filter. */
  after: number | null
  onBeforeChange: (next: number | null) => void
  onAfterChange: (next: number | null) => void
  /** Inclusive lower bound for the inputs (also the default when toggled on). */
  minYear: number
  /** Inclusive upper bound for the inputs (also the default for `after`). */
  maxYear: number
}

interface YearFieldProps {
  id: string
  label: string
  value: number | null
  defaultOn: number
  onChange: (next: number | null) => void
  min: number
  max: number
}

function YearField({
  id,
  label,
  value,
  defaultOn,
  onChange,
  min,
  max,
}: YearFieldProps) {
  const enabled = value !== null
  return (
    <div className="flex items-center gap-2">
      <Label htmlFor={id} className="flex-1">
        {label}
      </Label>
      <Switch
        aria-label={`Apply ${label} filter`}
        checked={enabled}
        onCheckedChange={(on) => onChange(on ? defaultOn : null)}
      />
      <Input
        id={id}
        type="number"
        min={min}
        max={max}
        step={1}
        value={value ?? ''}
        disabled={!enabled}
        onChange={(e) => {
          const raw = e.target.value
          if (raw === '') {
            onChange(null)
            return
          }
          // FP13 § E2: guard against NaN (paste of "abc") and clamp out-of-
          // range values (paste of "1850" or "9999"). HTML `min`/`max` are
          // spinner-only constraints, not validation.
          const n = Number(raw)
          if (Number.isNaN(n)) return
          onChange(n < min ? min : n > max ? max : n)
        }}
        className="w-24"
      />
    </div>
  )
}

export function YearRangeEditor({
  before,
  after,
  onBeforeChange,
  onAfterChange,
  minYear,
  maxYear,
}: YearRangeEditorProps) {
  return (
    <div className="flex flex-col gap-2">
      <YearField
        id="filters-drop-year-before"
        label="Drop games before year"
        value={before}
        defaultOn={minYear}
        onChange={onBeforeChange}
        min={minYear}
        max={maxYear}
      />
      <YearField
        id="filters-drop-year-after"
        label="Drop games after year"
        value={after}
        defaultOn={maxYear}
        onChange={onAfterChange}
        min={minYear}
        max={maxYear}
      />
    </div>
  )
}
