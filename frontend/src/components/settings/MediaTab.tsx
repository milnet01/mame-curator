import { useMemo, useState } from "react";

import { Label } from "@/components/ui/label";
import { ConfigureSourceKeyModal } from "@/components/settings/ConfigureSourceKeyModal";
import { DownloadPackModal } from "@/components/settings/DownloadPackModal";
import { DragReorderList } from "@/components/settings/DragReorderList";
import { FolderField } from "@/components/settings/FolderField";
import { MediaSourceRow } from "@/components/settings/MediaSourceRow";
import { PrefSwitch } from "@/components/settings/PrefSwitch";
import { useMediaSources } from "@/hooks/useMediaSources";
import { strings } from "@/strings";
import type { AppConfigResponse, SourceReadinessRow } from "@/api/types";

type MediaCfg = AppConfigResponse["media"];

// mame-curator-1084 — the backend registry always re-appends this source
// (`MediaSourceRegistry.chain_for`), so its toggle is locked on.
const BASELINE_SOURCE = "libretro";

interface MediaTabProps {
  media: MediaCfg;
  onChange: <K extends keyof MediaCfg>(key: K, value: MediaCfg[K]) => void;
}

export function MediaTab({ media, onChange }: MediaTabProps) {
  const [configureSource, setConfigureSource] = useState<string | null>(null);
  const [packOpen, setPackOpen] = useState(false);

  const { data: readiness } = useMediaSources();
  const readinessByName = useMemo(
    () =>
      Object.fromEntries(
        (readiness?.sources ?? []).map((r): [string, SourceReadinessRow] => [
          r.name,
          r,
        ]),
      ),
    [readiness],
  );
  // mame-curator-1084 — known sources the user has turned off (not in the
  // fallback chain). The backend readiness surface returns them in_chain=false,
  // already alphabetised; we render them below the reorderable list.
  const unconfigured = useMemo(
    () => (readiness?.sources ?? []).filter((r) => !r.in_chain),
    [readiness],
  );

  // Add/remove a source from the media.sources fallback chain (PATCH via
  // onChange). Toggling on appends to the end (lowest priority); reorder moves
  // it up. Toggling off drops it. libretro is locked, so it never reaches here.
  const toggleSource = (name: string, next: boolean) => {
    if (next) {
      if (!media.sources.includes(name))
        onChange("sources", [...media.sources, name]);
    } else {
      onChange(
        "sources",
        media.sources.filter((n) => n !== name),
      );
    }
  };

  return (
    <>
      <PrefSwitch
        id="media-fetch-videos"
        label={strings.settings.mediaLabels.fetch_videos}
        checked={media.fetch_videos}
        onChange={(v) => onChange("fetch_videos", v)}
      />
      <FolderField
        id="media-cache-dir"
        label={strings.settings.mediaCacheLabel}
        browseLabel={strings.settings.mediaCacheBrowseLabel}
        value={media.cache_dir}
        onCommit={(v) => onChange("cache_dir", v ?? "")}
      />
      {/* mame-curator-1081 — progettoSnaps pack folder; kept in sync with the
          folder `refresh-snaps` downloads into so the source can't miss it. */}
      <FolderField
        id="media-snaps-dir"
        label={strings.settings.mediaSnapsLabel}
        browseLabel={strings.settings.mediaSnapsBrowseLabel}
        help={strings.settings.mediaSnapsHelp}
        value={media.snaps_dir}
        onCommit={(v) => onChange("snaps_dir", v ?? "")}
      />
      {/* mame-curator-1126 — artwork ES-DE / RetroArch already scraped. */}
      <FolderField
        id="media-esde-dir"
        label={strings.settings.mediaEsdeLabel}
        browseLabel={strings.settings.mediaEsdeBrowseLabel}
        help={strings.settings.mediaEsdeHelp}
        value={media.esde_media_dir}
        onCommit={(v) => onChange("esde_media_dir", v)}
        optional
      />
      <FolderField
        id="media-retroarch-thumbnails-dir"
        label={strings.settings.mediaRetroarchLabel}
        browseLabel={strings.settings.mediaRetroarchBrowseLabel}
        help={strings.settings.mediaRetroarchHelp}
        value={media.retroarch_thumbnails_dir}
        onCommit={(v) => onChange("retroarch_thumbnails_dir", v)}
        optional
      />

      {/* P10 chunk 10 — art-source priority list with live readiness. */}
      <div className="flex flex-col gap-2">
        <div>
          <Label>{strings.settings.mediaSources.sectionLabel}</Label>
          <p className="text-xs text-muted-foreground">
            {strings.settings.mediaSources.sectionHelp}
          </p>
        </div>
        <DragReorderList
          ariaLabel={strings.settings.mediaSources.reorderAriaLabel}
          items={media.sources}
          onChange={(next) => onChange("sources", next)}
          renderItem={(name) => {
            const row = readinessByName[name];
            return row ? (
              <MediaSourceRow
                row={row}
                onConfigure={setConfigureSource}
                onDownloadPack={() => setPackOpen(true)}
                onToggle={toggleSource}
                locked={name === BASELINE_SOURCE}
              />
            ) : (
              <span>{name}</span>
            );
          }}
        />

        {/* mame-curator-1084 — known sources currently off (not in the chain). */}
        {unconfigured.length > 0 && (
          <div className="mt-2 flex flex-col gap-2">
            <div>
              <Label>{strings.settings.mediaSources.unconfiguredLabel}</Label>
              <p className="text-xs text-muted-foreground">
                {strings.settings.mediaSources.unconfiguredHelp}
              </p>
            </div>
            <ul className="flex flex-col gap-1">
              {unconfigured.map((row) => (
                <li
                  key={row.name}
                  className="flex items-center rounded-md border px-3 py-2"
                >
                  <MediaSourceRow
                    row={row}
                    onConfigure={setConfigureSource}
                    onDownloadPack={() => setPackOpen(true)}
                    onToggle={toggleSource}
                  />
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {configureSource !== null && (
        <ConfigureSourceKeyModal
          open
          onOpenChange={(o) => {
            if (!o) setConfigureSource(null);
          }}
          sourceName={configureSource}
        />
      )}
      <DownloadPackModal open={packOpen} onOpenChange={setPackOpen} />
    </>
  );
}
