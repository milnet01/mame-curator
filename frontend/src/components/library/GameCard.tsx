import { useState } from 'react'
import {
  AlertTriangle,
  Ban,
  CheckCircle,
  Disc,
  GitBranch,
  HelpCircle,
  Pencil,
  StickyNote,
  type LucideIcon,
} from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { strings } from '@/strings'
import type {
  Badge,
  GameCard as GameCardType,
  ReviewBadgeKind,
  ReviewStateValue,
} from '@/api/types'

interface GameCardProps {
  card: GameCardType
  focused?: boolean
  inCart: boolean
  onOpen: () => void
  onAdd: (shortName: string) => void
  /** P14 — per-card review state, rendered as a frontend-only badge in
   *  the same top-right slot as the existing backend-emitted badges. */
  reviewState?: ReviewStateValue
}

const BADGE_LABELS: Record<Badge, string> = {
  contested: strings.library.badges.contested,
  overridden: strings.library.badges.overridden,
  chd_missing: strings.library.badges.chd_missing,
  bios_missing: strings.library.badges.bios_missing,
  has_notes: strings.library.badges.has_notes,
}

// FP11 § D5: emoji-as-functional-UI replaced by Lucide icons per
// coding-standards § 4 ("No emojis as functional UI; use proper
// icons (lucide-react)"). Each icon's accessible name lives on the
// wrapping `<li aria-label>`; the icon itself is `aria-hidden`.
const BADGE_ICONS: Record<Badge, LucideIcon> = {
  contested: GitBranch,
  overridden: Pencil,
  chd_missing: Disc,
  bios_missing: AlertTriangle,
  has_notes: StickyNote,
}

// P14 — parallel maps for the frontend-only review-state badges. NOT
// merged into BADGE_LABELS / BADGE_ICONS because those are typed
// `Record<Badge, ...>` and the TS exhaustiveness check across the five
// backend-emitted values is load-bearing for the type-sync gate.
const REVIEW_BADGE_LABELS: Record<ReviewBadgeKind, string> = {
  reviewed: strings.library.badges.reviewed,
  skipped: strings.library.badges.skipped,
  'needs-decision': strings.library.badges.needsDecision,
}

const REVIEW_BADGE_ICONS: Record<ReviewBadgeKind, LucideIcon> = {
  reviewed: CheckCircle,
  skipped: Ban,
  'needs-decision': HelpCircle,
}

const REVIEW_BADGE_TINT: Record<ReviewBadgeKind, string> = {
  reviewed: 'text-emerald-500',
  skipped: 'text-rose-500',
  'needs-decision': 'text-amber-500',
}

export function GameCard({
  card,
  focused = false,
  inCart,
  onOpen,
  onAdd,
  reviewState,
}: GameCardProps) {
  const [imgFailed, setImgFailed] = useState(false)
  const flyerSrc = `/media/${encodeURIComponent(card.short_name)}/boxart`
  // FP20-H: stable id wires aria-labelledby on the outer card to the
  // inner heading, so the button's accessible name is exactly the
  // game description — not the screen-reader-clobbering aria-label
  // that used to live on the wrapper.
  // FP25-K(7): uniqueness invariant — `short_name` must be unique
  // within the rendered DOM. Inside a single MAME DAT the names are
  // globally unique by spec, but a cart drawer and the main grid CAN
  // render the same card concurrently. If a future surface composes
  // two GameCards for the same short_name into one tree, the second
  // `<heading id={titleId}>` collides with the first and assistive
  // tech announces the wrong title. Mitigation when that happens:
  // prefix `titleId` with the calling surface ("grid", "drawer") so
  // duplicates differ across surfaces.
  const titleId = `gamecard-title-${card.short_name}`

  // FP24-E + Q: outer wrapper is role="button" div, not a native
  // <button>. The inner +Add is itself a real button and nested
  // <button> is invalid HTML5 / undefined AT behaviour. Composite
  // button keyboard semantics (Enter + Space) are restored via
  // onKeyDown; focus-visible ring lives on the wrapper so it has
  // visible focus to attach to (FP11 § D4's `className="contents"`
  // ate the button's CSS box, leaving the ring nowhere to render).
  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onOpen()
    }
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={handleKeyDown}
      aria-labelledby={titleId}
      className="text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
    >
      <Card
        className={cn(
          'flex h-full cursor-pointer flex-col overflow-hidden transition-shadow hover:shadow-lg',
          focused && 'ring-2 ring-ring',
        )}
      >
        {/* FP14: image area uses flex-1 + object-contain instead of
            aspect-[3/4] + object-cover. Old layout pushed total card
            height above the virtualizer rowHeight (clipping the title
            via overflow-hidden); flex-1 makes the image fill the row
            after CardContent claims its natural size. object-contain
            preserves both portrait boxart and landscape marquee art. */}
        <div className="relative min-h-0 flex-1 bg-muted">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              onAdd(card.short_name)
            }}
            aria-label={
              inCart
                ? strings.library.cart.removeFromCart(card.description)
                : strings.library.cart.addToCart(card.description)
            }
            className="absolute left-1 top-1 z-10 rounded bg-background/90 px-2 py-1 text-xs font-medium shadow-sm hover:bg-background"
          >
            {inCart ? strings.library.cart.added : strings.library.cart.add}
          </button>
          {imgFailed ? (
            <div className="flex h-full items-center justify-center px-3 text-center text-sm font-semibold leading-tight text-muted-foreground">
              {card.description}
            </div>
          ) : (
            <img
              src={flyerSrc}
              // FP20-H: decorative — the <h3> already names the card
              // via aria-labelledby. A duplicate alt would re-announce
              // the description to AT users on hover/focus.
              alt=""
              data-testid={`gamecard-img-${card.short_name}`}
              loading="lazy"
              onError={() => setImgFailed(true)}
              className="h-full w-full object-contain"
            />
          )}
          {(card.badges.length > 0 || reviewState !== undefined) && (
            <ul className="absolute right-1 top-1 flex flex-col gap-1">
              {card.badges.map((b) => {
                const Icon = BADGE_ICONS[b]
                return (
                  <li
                    key={b}
                    aria-label={BADGE_LABELS[b]}
                    title={BADGE_LABELS[b]}
                    className="flex h-6 w-6 items-center justify-center rounded-full bg-background/90 shadow-sm"
                  >
                    <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                  </li>
                )
              })}
              {reviewState !== undefined && (
                <li
                  key={`review-${reviewState}`}
                  data-testid={`review-badge-${reviewState}`}
                  aria-label={REVIEW_BADGE_LABELS[reviewState]}
                  title={REVIEW_BADGE_LABELS[reviewState]}
                  className="flex h-6 w-6 items-center justify-center rounded-full bg-background/90 shadow-sm"
                >
                  {(() => {
                    const ReviewIcon = REVIEW_BADGE_ICONS[reviewState]
                    return (
                      <ReviewIcon
                        className={cn('h-3.5 w-3.5', REVIEW_BADGE_TINT[reviewState])}
                        aria-hidden="true"
                      />
                    )
                  })()}
                </li>
              )}
            </ul>
          )}
        </div>
        <CardContent className="flex flex-shrink-0 flex-col gap-0.5 px-3 py-2">
          <h3
            id={titleId}
            className="line-clamp-2 text-sm font-semibold leading-tight"
          >
            {card.description}
          </h3>
          <p className="font-mono text-xs text-muted-foreground">
            {card.short_name}
          </p>
          <p className="text-xs text-muted-foreground">
            {[card.year, card.publisher].filter(Boolean).join(' · ') || '—'}
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
