import { useState } from 'react'
import {
  AlertTriangle,
  Disc,
  GitBranch,
  Pencil,
  StickyNote,
  type LucideIcon,
} from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { strings } from '@/strings'
import type { Badge, GameCard as GameCardType } from '@/api/types'

interface GameCardProps {
  card: GameCardType
  focused?: boolean
  onOpen: () => void
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

export function GameCard({ card, focused = false, onOpen }: GameCardProps) {
  const [imgFailed, setImgFailed] = useState(false)
  const flyerSrc = `/media/${encodeURIComponent(card.short_name)}/boxart`
  const altText = strings.library.flyerAlt(card.description)

  return (
    // FP11 § D4: native <button> wrapper restores focus-visible /
    // Enter+Space activation / form-context semantics that the prior
    // div-with-role="button" lost. `className="contents"` makes the
    // button render its children inline, leaving the Card layout
    // pixel-identical to the pre-fix render.
    <button
      type="button"
      onClick={onOpen}
      aria-label={card.description}
      className="contents text-left"
    >
      <Card
        className={cn(
          'flex cursor-pointer flex-col overflow-hidden transition-shadow hover:shadow-lg focus-visible:ring-2 focus-visible:ring-ring',
          focused && 'ring-2 ring-ring',
        )}
      >
        <div className="relative aspect-[3/4] bg-muted">
          {imgFailed ? (
            <div className="flex h-full items-center justify-center px-2 text-center text-xs text-muted-foreground">
              {strings.library.placeholderFlyer}
            </div>
          ) : (
            <img
              src={flyerSrc}
              alt={altText}
              loading="lazy"
              onError={() => setImgFailed(true)}
              className="h-full w-full object-cover"
            />
          )}
          {card.badges.length > 0 && (
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
            </ul>
          )}
        </div>
        <CardContent className="flex flex-col gap-1 px-3 py-2">
          <h3 className="line-clamp-2 text-sm font-semibold leading-tight">
            {card.description}
          </h3>
          <p className="text-xs text-muted-foreground">
            {[card.year, card.publisher].filter(Boolean).join(' · ') || '—'}
          </p>
        </CardContent>
      </Card>
    </button>
  )
}
