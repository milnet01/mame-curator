import { useState } from 'react'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { strings } from '@/strings'
import type { GameCard, OverridePostRequest } from '@/api/types'

interface AlternativesDrawerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  winner: GameCard
  alternatives: GameCard[]
  onOverride: (request: OverridePostRequest) => void
  /** FP19: optional Launch handler. Hides the button when not provided
   *  (e.g. unit tests that don't mock the launch endpoint). */
  onLaunch?: (shortName: string) => void
  /** True while the launch mutation is in flight. */
  launching?: boolean
}

function AlternativeRow({
  alt,
  isWinner,
  onPick,
}: {
  alt: GameCard
  isWinner: boolean
  onPick: () => void
}) {
  const [imgFailed, setImgFailed] = useState(false)
  const buttonName = isWinner
    ? strings.alternatives.selectedAriaLabel(alt.description)
    : strings.alternatives.useAriaLabel(alt.description)
  return (
    <Card className={cn(isWinner && 'border-primary')}>
      <CardContent className="flex items-center gap-3 p-3">
        {/* FP11 § B6: design §8 demands "side-by-side strip of parent +
            clones with media". 64×80 thumbnails per row keep the drawer
            compact while still surfacing the visual cue. */}
        <div className="h-20 w-16 flex-shrink-0 overflow-hidden rounded bg-muted">
          {imgFailed ? (
            <div className="flex h-full items-center justify-center px-1 text-center text-[10px] text-muted-foreground">
              {strings.library.placeholderFlyer}
            </div>
          ) : (
            <img
              src={`/media/${encodeURIComponent(alt.short_name)}/boxart`}
              alt={strings.alternatives.flyerAlt(alt.description)}
              loading="lazy"
              onError={() => setImgFailed(true)}
              className="h-full w-full object-cover"
            />
          )}
        </div>
        <div className="flex flex-1 flex-col">
          <span className="text-sm font-medium">{alt.description}</span>
          <span className="text-xs text-muted-foreground">
            {[alt.short_name, alt.year, alt.publisher]
              .filter(Boolean)
              .join(' · ')}
          </span>
        </div>
        <Button
          size="sm"
          variant={isWinner ? 'secondary' : 'default'}
          disabled={isWinner}
          aria-label={buttonName}
          onClick={onPick}
        >
          {isWinner
            ? strings.alternatives.pickedLabel
            : strings.alternatives.overrideButton}
        </Button>
      </CardContent>
    </Card>
  )
}

export function AlternativesDrawer({
  open,
  onOpenChange,
  winner,
  alternatives,
  onOverride,
  onLaunch,
  launching = false,
}: AlternativesDrawerProps) {
  const parent = winner.short_name
  const handleClick = (alt: GameCard) => {
    onOverride({ parent, winner: alt.short_name })
    onOpenChange(false)
  }

  // FP11 § B5: spec / design §8 makes 1-element-list and N-element-list
  // distinct UX. With one alternative (= just the winner), show
  // "This is the only version" and skip the row list entirely. With
  // multiple, show the count line and the rows.
  const onlyOne = alternatives.length === 1

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="flex w-full max-w-md flex-col gap-4">
        <SheetHeader>
          <SheetTitle>{strings.alternatives.drawerTitle}</SheetTitle>
          <SheetDescription>
            {onlyOne
              ? strings.alternatives.onlyVersionText
              : strings.alternatives.familySummary(alternatives.length)}
          </SheetDescription>
        </SheetHeader>

        {!onlyOne && (
          <ul className="flex flex-col gap-2">
            {alternatives.map((alt) => (
              <li key={alt.short_name}>
                <AlternativeRow
                  alt={alt}
                  isWinner={alt.short_name === winner.short_name}
                  onPick={() => handleClick(alt)}
                />
              </li>
            ))}
          </ul>
        )}

        {/* FP19: Launch button — spawns RetroArch with the current
            winner's ROM. Hidden when onLaunch isn't wired (unit tests). */}
        {onLaunch && (
          <Button
            onClick={() => onLaunch(winner.short_name)}
            disabled={launching}
            className="mt-auto"
          >
            {launching
              ? strings.alternatives.launching
              : strings.alternatives.launch}
          </Button>
        )}
      </SheetContent>
    </Sheet>
  )
}
