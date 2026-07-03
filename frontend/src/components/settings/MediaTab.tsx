import { useMemo, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ConfigureSourceKeyModal } from '@/components/settings/ConfigureSourceKeyModal'
import { DownloadPackModal } from '@/components/settings/DownloadPackModal'
import { DragReorderList } from '@/components/settings/DragReorderList'
import { FsBrowser } from '@/components/settings/FsBrowser'
import { MediaSourceRow } from '@/components/settings/MediaSourceRow'
import { PrefSwitch } from '@/components/settings/PrefSwitch'
import { useMediaSources } from '@/hooks/useMediaSources'
import { strings } from '@/strings'
import type { AppConfigResponse, SourceReadinessRow } from '@/api/types'

type MediaCfg = AppConfigResponse['media']

interface MediaTabProps {
  media: MediaCfg
  onChange: <K extends keyof MediaCfg>(key: K, value: MediaCfg[K]) => void
}

export function MediaTab({ media, onChange }: MediaTabProps) {
  const [cacheDirDraft, setCacheDirDraft] = useState(media.cache_dir)
  const [browseOpen, setBrowseOpen] = useState(false)
  const [snapsDirDraft, setSnapsDirDraft] = useState(media.snaps_dir)
  const [snapsBrowseOpen, setSnapsBrowseOpen] = useState(false)
  const [configureSource, setConfigureSource] = useState<string | null>(null)
  const [packOpen, setPackOpen] = useState(false)

  const { data: readiness } = useMediaSources()
  const readinessByName = useMemo(
    () =>
      Object.fromEntries(
        (readiness?.sources ?? []).map((r): [string, SourceReadinessRow] => [r.name, r]),
      ),
    [readiness],
  )

  return (
    <>
      <PrefSwitch
        id="media-fetch-videos"
        label={strings.settings.mediaLabels.fetch_videos}
        checked={media.fetch_videos}
        onChange={(v) => onChange('fetch_videos', v)}
      />
      <div className="flex flex-col gap-1">
        <Label htmlFor="media-cache-dir">{strings.settings.mediaCacheLabel}</Label>
        <div className="flex items-center gap-2">
          <Input
            id="media-cache-dir"
            value={cacheDirDraft}
            onChange={(e) => setCacheDirDraft(e.target.value)}
            onBlur={() => {
              if (cacheDirDraft !== media.cache_dir) {
                onChange('cache_dir', cacheDirDraft)
              }
            }}
          />
          <Button
            variant="outline"
            onClick={() => setBrowseOpen(true)}
            aria-label={strings.settings.mediaCacheBrowseLabel}
          >
            {strings.settings.fsBrowserBrowse}
          </Button>
        </div>
      </div>
      {browseOpen && (
        <FsBrowser
          open
          onOpenChange={setBrowseOpen}
          onPick={(picked) => {
            setCacheDirDraft(picked)
            onChange('cache_dir', picked)
          }}
          initialPath={media.cache_dir || undefined}
        />
      )}

      {/* mame-curator-1081 — progettoSnaps pack folder; kept in sync with the
          folder `refresh-snaps` downloads into so the source can't miss it. */}
      <div className="flex flex-col gap-1">
        <Label htmlFor="media-snaps-dir">{strings.settings.mediaSnapsLabel}</Label>
        <div className="flex items-center gap-2">
          <Input
            id="media-snaps-dir"
            value={snapsDirDraft}
            onChange={(e) => setSnapsDirDraft(e.target.value)}
            onBlur={() => {
              if (snapsDirDraft !== media.snaps_dir) {
                onChange('snaps_dir', snapsDirDraft)
              }
            }}
          />
          <Button
            variant="outline"
            onClick={() => setSnapsBrowseOpen(true)}
            aria-label={strings.settings.mediaSnapsBrowseLabel}
          >
            {strings.settings.fsBrowserBrowse}
          </Button>
        </div>
        <p className="text-xs text-muted-foreground">{strings.settings.mediaSnapsHelp}</p>
      </div>
      {snapsBrowseOpen && (
        <FsBrowser
          open
          onOpenChange={setSnapsBrowseOpen}
          onPick={(picked) => {
            setSnapsDirDraft(picked)
            onChange('snaps_dir', picked)
          }}
          initialPath={media.snaps_dir || undefined}
        />
      )}

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
          onChange={(next) => onChange('sources', next)}
          renderItem={(name) => {
            const row = readinessByName[name]
            return row ? (
              <MediaSourceRow
                row={row}
                onConfigure={setConfigureSource}
                onDownloadPack={() => setPackOpen(true)}
              />
            ) : (
              <span>{name}</span>
            )
          }}
        />
      </div>

      {configureSource !== null && (
        <ConfigureSourceKeyModal
          open
          onOpenChange={(o) => {
            if (!o) setConfigureSource(null)
          }}
          sourceName={configureSource}
        />
      )}
      <DownloadPackModal open={packOpen} onOpenChange={setPackOpen} />
    </>
  )
}
