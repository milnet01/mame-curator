import { Link } from 'react-router'
import { strings } from '@/strings'

interface ListxmlBannerProps {
  /**
   * `true` when ``setupCheck.reference_files.listxml.exists`` is true,
   * `false` when the file is missing or the path is unset, `undefined`
   * while the setup-check query is still loading. The banner only
   * renders when ``exists === false``; loading and present-state both
   * suppress it so the user never sees a flash of warning during boot.
   */
  exists: boolean | undefined
}

/**
 * FP23 — surfaces the silent failure mode where ``paths.listxml`` is
 * unset in ``config.yaml`` and the runner therefore can't collapse
 * parent/clone groups (ADR-0002 fallback returns an empty
 * ``cloneof_map`` so every machine self-parents). Symptom: the library
 * shows ~21k cards instead of the post-collapse winner count. The
 * banner makes that state visible and points at the fix.
 */
export function ListxmlBanner({ exists }: ListxmlBannerProps) {
  if (exists !== false) return null
  return (
    <div
      role="alert"
      className="mx-4 mt-2 flex flex-wrap items-center gap-3 rounded border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm"
    >
      <span className="font-medium">{strings.library.listxmlMissing.title}</span>
      <span className="text-muted-foreground">
        {strings.library.listxmlMissing.body}
      </span>
      <Link
        to="/settings"
        className="ml-auto rounded bg-amber-500/20 px-2 py-1 text-xs font-medium hover:bg-amber-500/30"
      >
        {strings.library.listxmlMissing.cta}
      </Link>
    </div>
  )
}
