/**
 * mame-curator-1217 — tick the languages to keep, then Done, or keep every
 * language. The /start guide's step and the Settings guide both use it.
 */
import { useState } from "react";
import { GuideAction } from "./GuideAction";
import { ChoiceLabel } from "./settings/SettingsStep";
import { useLanguages } from "@/hooks/useLanguages";
import { apiErrorMessage } from "@/lib/apiErrorToast";
import { strings } from "@/strings";

interface LanguagePickerProps {
  /** The languages kept now; empty keeps every language. */
  current: string[];
  busy?: boolean;
  /** Why the last save failed, shown beside Done. */
  error?: string | null;
  onSave: (next: string[]) => void;
}

export function LanguagePicker({
  current,
  busy,
  error,
  onSave,
}: LanguagePickerProps) {
  const languages = useLanguages();
  const [ticked, setTicked] = useState(() => new Set(current));
  const listed = languages.data?.languages ?? [];

  const toggle = (name: string) =>
    setTicked((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  // The list's order (most games first); a kept name the list lacks stays.
  const done = () => {
    const names = listed.map((l) => l.name);
    onSave([
      ...names.filter((n) => ticked.has(n)),
      ...[...ticked].filter((n) => !names.includes(n)),
    ]);
  };

  return (
    <>
      {listed.length > 0 && (
        <p className="text-xl">{strings.guide.languages.help}</p>
      )}
      <GuideAction onClick={() => onSave([])} busy={busy}>
        <ChoiceLabel
          label={strings.guide.languages.keepAll}
          mark={current.length === 0 ? strings.guide.settings.inUse : undefined}
        />
      </GuideAction>
      {languages.isPending && (
        <p className="text-xl">{strings.guide.loading}</p>
      )}
      {languages.isError && (
        <p role="alert" className="text-xl text-destructive">
          {apiErrorMessage(languages.error)}
        </p>
      )}
      {languages.isSuccess && listed.length === 0 && (
        <p className="text-xl">{strings.guide.languages.none}</p>
      )}
      {listed.map(({ name }) => (
        <GuideAction
          key={name}
          pressed={ticked.has(name)}
          onClick={() => toggle(name)}
        >
          <ChoiceLabel
            label={name}
            mark={ticked.has(name) ? strings.guide.languages.chosen : undefined}
          />
        </GuideAction>
      ))}
      {error && (
        <p role="alert" className="text-xl text-destructive">
          {error}
        </p>
      )}
      <GuideAction primary onClick={done} busy={busy}>
        {strings.guide.languages.done}
      </GuideAction>
    </>
  );
}
