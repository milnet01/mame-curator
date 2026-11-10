/**
 * mame-curator-1217 — the Filters tab's languages to keep: one toggle per
 * language languages.ini names, most games first. None pressed keeps all.
 */
import { Button } from "@/components/ui/button";
import { useLanguages } from "@/hooks/useLanguages";
import { apiErrorMessage } from "@/lib/apiErrorToast";
import { strings } from "@/strings";

interface LanguagesFieldProps {
  value: string[];
  onChange: (next: string[]) => void;
}

export function LanguagesField({ value, onChange }: LanguagesFieldProps) {
  const languages = useLanguages();
  const toggle = (name: string) =>
    onChange(
      value.includes(name) ? value.filter((n) => n !== name) : [...value, name],
    );
  return (
    <div
      role="group"
      aria-labelledby="filters-keep-languages-label"
      aria-describedby="filters-keep-languages-help"
      className="flex flex-col gap-1"
    >
      <span id="filters-keep-languages-label" className="text-sm font-medium">
        {strings.settings.keepLanguages.label}
      </span>
      <p
        id="filters-keep-languages-help"
        className="text-sm text-muted-foreground"
      >
        {strings.settings.keepLanguages.help}
      </p>
      <div className="flex flex-wrap gap-2">
        {languages.data?.languages.map(({ name }) => (
          <Button
            key={name}
            type="button"
            size="sm"
            variant={value.includes(name) ? "default" : "outline"}
            aria-pressed={value.includes(name)}
            onClick={() => toggle(name)}
          >
            {name}
          </Button>
        ))}
      </div>
      {languages.isError && (
        <p role="alert" className="text-sm text-destructive">
          {apiErrorMessage(languages.error)}
        </p>
      )}
    </div>
  );
}
