import { useState, type KeyboardEvent } from 'react'
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

const BADGE_GLYPHS: Record<Badge, string> = {
  contested: '🔀',
  overridden: '✏️',
  chd_missing: '💿',
  bios_missing: '⚠️',
  has_notes: '📝',
}

export function GameCard({ card, focused = false, onOpen }: GameCardProps) {
  const [imgFailed, setImgFailed] = useState(false)
  const flyerSrc = `/media/${encodeURIComponent(card.short_name)}/boxart`
  const altText = strings.library.flyerAlt(card.description)

  const handleKey = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onOpen()
    }
  }

  return (
    <Card
      role="button"
      tabIndex={0}
      aria-label={card.description}
      onClick={onOpen}
      onKeyDown={handleKey}
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
            {card.badges.map((b) => (
              <li
                key={b}
                aria-label={BADGE_LABELS[b]}
                title={BADGE_LABELS[b]}
                className="flex h-6 w-6 items-center justify-center rounded-full bg-background/90 text-sm shadow-sm"
              >
                <span aria-hidden="true">{BADGE_GLYPHS[b]}</span>
              </li>
            ))}
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
  )
}
