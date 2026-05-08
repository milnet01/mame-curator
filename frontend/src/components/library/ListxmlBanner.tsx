import { Link } from 'react-router'
import { strings } from '@/strings'

interface ListxmlBannerProps {
  /** ``true`` when the file at paths.listxml exists; ``false`` if missing or
   * unset; ``undefined`` while loading. */
  exists: boolean | undefined
  /** P15: ``len(world.cloneof_map)`` from /api/setup/check.cloneof_map_size.
   * When 0 with file present, listxml parsed but contained zero cloneof
   * entries — a separate failure mode from the file being missing. */
  cloneofMapSize?: number
}

export function ListxmlBanner({ exists, cloneofMapSize }: ListxmlBannerProps) {
  const fileMissing = exists === false
  const parsedEmpty = exists === true && cloneofMapSize === 0
  if (!fileMissing && !parsedEmpty) return null

  const body = parsedEmpty
    ? strings.library.listxmlMissing.emptyParseBody
    : strings.library.listxmlMissing.body

  return (
    <div
      // FP24-Y: role="status" — informational notice that polite live-
      // region etiquette suits, not the assertive role="alert" reserved
      // for time-sensitive alerts (errors interrupting work).
      role="status"
      className="mx-4 mt-2 flex flex-wrap items-center gap-3 rounded border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm"
    >
      <span className="font-medium">{strings.library.listxmlMissing.title}</span>
      <span className="text-muted-foreground">{body}</span>
      <Link
        to="/settings"
        className="ml-auto rounded bg-amber-500/20 px-2 py-1 text-xs font-medium hover:bg-amber-500/30"
      >
        {strings.library.listxmlMissing.cta}
      </Link>
    </div>
  )
}
