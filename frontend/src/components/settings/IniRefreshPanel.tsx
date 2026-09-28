import { Button } from "@/components/ui/button";
import { strings } from "@/strings";
import type { IniPreview } from "@/api/types";

interface IniRefreshPanelProps {
  onPreview: () => void;
  previewing: boolean;
  preview?: IniPreview;
  onApply: () => void;
  applying: boolean;
  applied: boolean;
}

function GameList({ title, names }: { title: string; names: string[] }) {
  if (names.length === 0) return null;
  return (
    <details className="text-sm">
      <summary className="cursor-pointer">{title}</summary>
      <ul className="ml-4 list-disc font-mono text-xs">
        {names.map((n) => (
          <li key={n}>{n}</li>
        ))}
      </ul>
    </details>
  );
}

/** mame-curator-1010 §4.6 — Preview → the games it would change → Apply. */
export function IniRefreshPanel({
  onPreview,
  previewing,
  preview,
  onApply,
  applying,
  applied,
}: IniRefreshPanelProps) {
  const changed = preview?.changed_files ?? [];
  return (
    <section
      aria-labelledby="ini-refresh-title"
      className="mt-4 flex flex-col gap-2 border-t pt-4"
    >
      <h3 id="ini-refresh-title" className="text-sm font-semibold">
        {strings.settings.updates.iniTitle}
      </h3>
      <p className="text-sm text-muted-foreground">
        {strings.settings.updates.iniBlurb}
      </p>
      <div>
        <Button
          variant="outline"
          size="sm"
          onClick={onPreview}
          disabled={previewing || applying}
        >
          {previewing
            ? strings.settings.updates.applying
            : strings.settings.updates.iniPreview}
        </Button>
      </div>
      {preview && !applied && (
        <div className="flex flex-col gap-2">
          {changed.length === 0 ? (
            <p className="text-sm">{strings.settings.updates.iniUpToDate}</p>
          ) : (
            <p className="text-sm">
              {strings.settings.updates.iniChanged(changed.join(", "))}
            </p>
          )}
          <GameList
            title={strings.settings.updates.iniAdded(
              preview.winners_added.length,
            )}
            names={preview.winners_added}
          />
          <GameList
            title={strings.settings.updates.iniRemoved(
              preview.winners_removed.length,
            )}
            names={preview.winners_removed}
          />
          {preview.failed.map(([name, url]) => (
            <p key={name} className="text-sm text-destructive">
              {strings.settings.updates.iniFailed(name)}{" "}
              <a
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="underline"
              >
                {url}
              </a>
            </p>
          ))}
          {changed.length > 0 && (
            <div>
              <Button size="sm" onClick={onApply} disabled={applying}>
                {applying
                  ? strings.settings.updates.applying
                  : strings.settings.updates.iniApply}
              </Button>
            </div>
          )}
        </div>
      )}
      {applied && (
        <p role="status" className="text-sm">
          {strings.settings.updates.iniApplied}
        </p>
      )}
    </section>
  );
}
