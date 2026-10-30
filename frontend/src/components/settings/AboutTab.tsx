import { strings } from "@/strings";

// mame-curator-1133: donations are optional; no feature is gated on them.
const SPONSOR_URL = "https://github.com/sponsors/milnet01";

interface AboutTabProps {
  /** The running backend's version; omitted until the setup check loads. */
  version?: string;
}

export function AboutTab({ version }: AboutTabProps) {
  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-muted-foreground">
        {strings.app.name} · {strings.app.tagline}
      </p>
      {version && (
        <p className="text-sm">{strings.settings.about.version(version)}</p>
      )}
      <p className="text-sm">{strings.settings.about.license}</p>
      <p className="text-sm">{strings.settings.about.disclaimer}</p>
      <a
        href={SPONSOR_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="self-start text-sm underline"
      >
        {strings.settings.about.support}{" "}
        <span className="text-muted-foreground">
          {strings.common.opensInNewTab}
        </span>
      </a>
    </div>
  );
}
