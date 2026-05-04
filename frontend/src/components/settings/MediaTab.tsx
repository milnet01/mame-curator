import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { FsBrowser } from '@/components/settings/FsBrowser'
import { PrefSwitch } from '@/components/settings/PrefSwitch'
import { strings } from '@/strings'
import type { AppConfigResponse } from '@/api/types'

type MediaCfg = AppConfigResponse['media']

interface MediaTabProps {
  media: MediaCfg
  onChange: <K extends keyof MediaCfg>(key: K, value: MediaCfg[K]) => void
}

export function MediaTab({ media, onChange }: MediaTabProps) {
  const [cacheDirDraft, setCacheDirDraft] = useState(media.cache_dir)
  const [browseOpen, setBrowseOpen] = useState(false)
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
    </>
  )
}
