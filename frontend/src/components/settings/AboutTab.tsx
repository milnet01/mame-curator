import { strings } from "@/strings";

// mame-curator-1133: donations are optional; no feature is gated on them.
const SPONSOR_URL = "https://github.com/sponsors/milnet01";

export function AboutTab() {
  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-muted-foreground">
        {strings.app.name} · {strings.app.tagline}
      </p>
      <p className="text-sm">{strings.settings.about.disclaimer}</p>
      <a
        href={SPONSOR_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="self-start text-sm underline"
      >
        {strings.settings.about.support}
      </a>
    </div>
  );
}
