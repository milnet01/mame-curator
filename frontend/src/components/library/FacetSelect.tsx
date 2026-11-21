import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { strings } from "@/strings";

/** FP17 § C: facet Select with a sentinel "(any)" first option that
 *  maps to null. Renders nothing when the options list is empty so the
 *  sidebar doesn't show a useless empty dropdown. */
export function FacetSelect({
  id,
  label,
  value,
  options,
  onChange,
}: {
  id: string;
  label: string;
  value: string | null;
  options: readonly string[];
  onChange: (next: string | null) => void;
}) {
  if (options.length === 0) return null;
  const ANY = "__any__";
  return (
    <div className="flex flex-col gap-1">
      <Label htmlFor={id}>{label}</Label>
      <Select
        value={value ?? ANY}
        onValueChange={(v) => onChange(v === ANY ? null : v)}
      >
        <SelectTrigger
          id={id}
          aria-label={label}
          // mame-curator-1141: the column's width, and a long name wraps
          // (all of it stays readable) instead of widening the column.
          className="w-full min-w-0 whitespace-normal text-left data-[size=default]:h-auto data-[size=default]:min-h-9 *:data-[slot=select-value]:line-clamp-none"
        >
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ANY}>
            {strings.library.filters.anyOption}
          </SelectItem>
          {options.map((o) => (
            <SelectItem key={o} value={o}>
              {o}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
