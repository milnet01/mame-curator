import { useMemo } from 'react'
import DOMPurify, { type Config } from 'dompurify'

import { strings } from '@/strings'
import { cn } from '@/lib/utils'
import type { HelpTopic } from '@/api/types'

// FP25-I: SCOPED DOMPurify INSTANCE — DO NOT EXPORT.
//
// Pre-FP25-I this module called ``DOMPurify.addHook(...)`` on the global
// singleton. Every other ``DOMPurify.sanitize(...)`` site in the bundle
// — current or future — silently inherited:
//   - the ``target="_blank"`` ``forceKeepAttr`` (so target survives
//     wherever the sanitizer is called),
//   - the rel="noopener noreferrer" injection on those anchors,
//   - the data:-URL strip on IMG/SOURCE/AUDIO/VIDEO/TRACK.
//
// No current victim, but the next developer adding a Markdown-rendered
// notes field would have been surprised. ``DOMPurify(window)`` returns
// a fresh, independent factory whose hooks don't touch the global; any
// other consumer that imports ``dompurify`` gets the un-hooked default.
const helpSanitizer = DOMPurify(window)

// FP20-L: harden the DOMPurify config beyond the P07 baseline.
//
//   ALLOWED_URI_REGEXP — only http/https/mailto schemes survive on
//     URI attributes (href, src). Strips data: payloads, javascript:
//     (already gone by default, but pinned), and any future scheme
//     that hasn't been explicitly allowlisted.
//   FORBID_TAGS — <style> and <form> are removed. The first kills
//     CSS-injection-based phishing/visual-spoofing inside help
//     content; the second defends against credential-phishing
//     forms that could otherwise auto-submit on render.
//   FORBID_ATTR — inline ``style="..."`` is stripped on every
//     element, complementing FORBID_TAGS for the same threat.
const HELP_SANITIZE_CONFIG: Config = {
  ALLOWED_URI_REGEXP: /^(?:https?|mailto):/i,
  FORBID_TAGS: ['style', 'form'],
  FORBID_ATTR: ['style'],
  // ``rel`` is added via ``ADD_ATTR`` so the afterSanitizeAttributes
  // hook can write to it; ``target`` is force-kept via the
  // uponSanitizeAttribute hook below (ADD_ATTR alone doesn't survive
  // the attribute-level sanitiser in DOMPurify v3+).
  ADD_ATTR: ['rel'],
}

// FP20-L: ``target="_blank"`` without ``rel="noopener"`` lets the new
// tab navigate ``window.opener`` (reverse-tabnabbing). The hook is
// installed once at module load on the HelpPage-scoped sanitizer
// (see FP25-I above). Hook reads the attribute (not the property) so
// server-rendered HTML strings — which never set the DOM property — are
// caught too.
// FP20-L: ``target`` is not in DOMPurify's default ALLOWED_ATTR; ADD_ATTR
// puts it in the set, but ``_isValidAttribute`` then strips it on a
// later pass. ``forceKeepAttr = true`` in the per-attribute hook
// bypasses both _isValidAttribute and the keepAttr default, so
// ``target="_blank"`` survives all the way to afterSanitizeAttributes.
helpSanitizer.addHook('uponSanitizeAttribute', (node, data) => {
  const el = node as Element
  if (
    data.attrName === 'target' &&
    el.tagName === 'A' &&
    data.attrValue === '_blank'
  ) {
    data.forceKeepAttr = true
    return
  }
  // FP20-L: DOMPurify's default ``DATA_URI_TAGS`` allowlist includes
  // ``img``, ``source``, ``audio``, ``video``, ``track`` — so a
  // ``src="data:..."`` survives the ALLOWED_URI_REGEXP check via that
  // special-case branch. The help content has no legitimate
  // data-URL need (boxart and screenshots route through
  // ``/media/...``), so strip data: srcs on those tags explicitly.
  // FP25-K(10): tagName casing — HTML elements expose ``tagName`` in
  // uppercase (DOM Living Standard § 4.4); SVG elements expose it in
  // its original case (e.g. ``circle``, not ``CIRCLE``). The uppercase
  // regex here is safe because DOMPurify's DATA_URI_TAGS allowlist is
  // HTML-only (no svg variants), so a hypothetical SVG ``<image>``
  // with ``href="data:..."`` is already handled by the ALLOWED_URI_REGEXP
  // path and never reaches this branch. If DOMPurify ever extends the
  // allowlist to SVG tags, swap to a case-insensitive comparison.
  if (
    data.attrName === 'src' &&
    /^(IMG|SOURCE|AUDIO|VIDEO|TRACK)$/.test(el.tagName) &&
    /^data:/i.test(data.attrValue)
  ) {
    data.keepAttr = false
  }
})

// FP20-L: with target preserved, set rel="noopener noreferrer" on
// every ``target="_blank"`` anchor to close the reverse-tabnabbing
// vector (the new tab can navigate ``window.opener`` otherwise).
// Duck-typed on tagName rather than ``instanceof Element`` so jsdom's
// separate Element global doesn't skip the hook in vitest.
helpSanitizer.addHook('afterSanitizeAttributes', (node) => {
  const el = node as Element
  // FP25-K(11): `Element.getAttribute` is part of the Element interface in
  // every DOM/jsdom version we run on, so the optional-chain operator was
  // dead — `el.getAttribute(...)` is callable unconditionally.
  if (el.tagName === 'A' && el.getAttribute('target') === '_blank') {
    el.setAttribute('rel', 'noopener noreferrer')
  }
})

interface HelpPageProps {
  topics: HelpTopic[]
  selectedSlug: string | null
  topicHtml: string
  onSelect: (slug: string) => void
  /** True while the topic body is being fetched. */
  topicLoading?: boolean
}

export function HelpPage({
  topics,
  selectedSlug,
  topicHtml,
  onSelect,
  topicLoading = false,
}: HelpPageProps) {
  // P07 § D: closes FP11 § H4 security debt. DOMPurify strips <script>,
  // javascript: URLs, and on-* event handlers before the HTML reaches
  // dangerouslySetInnerHTML. FP20-L tightens the config (HELP_SANITIZE_
  // CONFIG above) and installs a one-time rel="noopener noreferrer"
  // hook against reverse-tabnabbing. Memoised so re-renders don't
  // re-sanitize the same body — sanitization is the most expensive
  // thing this page does.
  const sanitizedHtml = useMemo(
    () => helpSanitizer.sanitize(topicHtml, HELP_SANITIZE_CONFIG),
    [topicHtml],
  )

  if (topics.length === 0) {
    return (
      <section className="flex flex-col items-center gap-2 p-8 text-center">
        <h1 className="text-2xl font-semibold">{strings.help.pageTitle}</h1>
        <p className="text-lg font-medium">{strings.help.emptyTitle}</p>
        <p className="text-sm text-muted-foreground">{strings.help.emptyHint}</p>
      </section>
    )
  }

  return (
    <section className="grid grid-cols-[16rem_1fr] gap-4 p-4">
      <aside>
        <h1 className="mb-3 text-2xl font-semibold">{strings.help.pageTitle}</h1>
        <ul className="flex flex-col gap-1">
          {topics.map((t) => {
            const isCurrent = selectedSlug === t.slug
            return (
              <li key={t.slug}>
                <button
                  type="button"
                  onClick={() => onSelect(t.slug)}
                  // FP11 § H5: aria-current signals the active topic to AT;
                  // the visual `font-semibold` carries the same meaning sighted.
                  aria-current={isCurrent ? 'page' : undefined}
                  className={cn(
                    'w-full rounded px-2 py-1 text-left text-sm hover:bg-muted',
                    isCurrent && 'bg-muted font-semibold',
                  )}
                >
                  {t.title}
                </button>
              </li>
            )
          })}
        </ul>
      </aside>

      <article className="prose prose-sm max-w-none dark:prose-invert">
        {topicLoading ? (
          <p className="text-sm text-muted-foreground">{strings.help.loadingTopic}</p>
        ) : (
          <div dangerouslySetInnerHTML={{ __html: sanitizedHtml }} />
        )}
      </article>
    </section>
  )
}
