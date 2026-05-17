import { useState } from 'react'
import { Link } from 'react-router'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { useKeyboard } from '@/hooks/useKeyboard'
import { cn } from '@/lib/utils'
import { strings } from '@/strings'
import type {
  GameCard,
  OverridePostRequest,
  ReviewStateValue,
  StateView,
} from '@/api/types'

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
  /** FP22-B: gates the Launch button on RetroArch config presence.
   *  ``true``  → button is enabled.
   *  ``false`` → button is disabled with an inline "Configure RetroArch
   *              in Settings → Paths" hint linking to /settings?tab=paths.
   *  ``undefined`` → setupCheck query still loading; treat as gated so a
   *  fast-clicker can't race the query into a 422. */
  retroarchConfigured?: boolean
  /** P14 — review-state cache for the drawer's per-row state read +
   *  R/S/? mutation callbacks. Optional so callers that don't wire
   *  review state (rare) render an unaltered drawer. */
  reviewState?: StateView
  onSetReviewState?: (shortName: string, state: ReviewStateValue) => void
  onClearReviewState?: (shortName: string) => void
}

const DRAWER_KEY_TO_STATE: Record<string, ReviewStateValue> = {
  r: 'reviewed',
  s: 'skipped',
  '?': 'needs-decision',
}

function AlternativeRow({
  alt,
  isWinner,
  onPick,
  highlighted = false,
}: {
  alt: GameCard
  isWinner: boolean
  onPick: () => void
  highlighted?: boolean
}) {
  const [imgFailed, setImgFailed] = useState(false)
  const buttonName = isWinner
    ? strings.alternatives.selectedAriaLabel(alt.description)
    : strings.alternatives.useAriaLabel(alt.description)
  return (
    <Card
      data-highlighted={highlighted || undefined}
      className={cn(
        isWinner && 'border-primary',
        highlighted && 'ring-2 ring-ring',
      )}
    >
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
  retroarchConfigured,
  reviewState,
  onSetReviewState,
  onClearReviewState,
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

  // P14 — highlight + R/S/? on drawer rows. Independent of grid focus.
  const [highlightedRowIndex, setHighlightedRowIndex] = useState(0)

  useKeyboard(
    open && !onlyOne
      ? [
          {
            combo: 'ArrowDown',
            handler: (e) => {
              e.preventDefault()
              setHighlightedRowIndex((prev) =>
                Math.min(alternatives.length - 1, prev + 1),
              )
            },
          },
          {
            combo: 'ArrowUp',
            handler: (e) => {
              e.preventDefault()
              setHighlightedRowIndex((prev) => Math.max(0, prev - 1))
            },
          },
          ...(['r', 's', '?'] as const).map((key) => ({
            combo: key,
            handler: (e: KeyboardEvent) => {
              if (!onSetReviewState) return
              const row = alternatives[highlightedRowIndex]
              if (!row) return
              e.preventDefault()
              const target = DRAWER_KEY_TO_STATE[key]!
              const current = reviewState?.entries[row.short_name]
              // INV-7 — drawer mutations do NOT auto-advance regardless
              // of walkthrough setting; the user typically opens the
              // drawer to compare clones individually.
              if (current === target) onClearReviewState?.(row.short_name)
              else onSetReviewState(row.short_name, target)
            },
          })),
        ]
      : [],
  )

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
            {alternatives.map((alt, idx) => (
              <li key={alt.short_name}>
                <AlternativeRow
                  alt={alt}
                  isWinner={alt.short_name === winner.short_name}
                  onPick={() => handleClick(alt)}
                  highlighted={idx === highlightedRowIndex}
                />
              </li>
            ))}
          </ul>
        )}

        {/* FP19: Launch button — spawns RetroArch with the current
            winner's ROM. Hidden when onLaunch isn't wired (unit tests).
            FP22-B: when retroarchConfigured is not strictly true the
            button is disabled and an inline hint surfaces the fix path
            (Settings → Paths). undefined is treated as "not yet known"
            and gates as well so a fast-clicker can't race the
            useSetupCheck query and get a 422 toast. */}
        {onLaunch && (
          <div className="mt-auto flex flex-col gap-2">
            <Button
              onClick={() => onLaunch(winner.short_name)}
              disabled={launching || retroarchConfigured !== true}
            >
              {launching
                ? strings.alternatives.launching
                : strings.alternatives.launch}
            </Button>
            {retroarchConfigured === false && (
              <p
                role="status"
                className="text-xs text-muted-foreground"
              >
                {strings.alternatives.launchConfigurePrefix}{' '}
                <Link
                  to="/settings?tab=paths"
                  className="underline"
                >
                  {strings.alternatives.launchConfigureLinkLabel}
                </Link>
                {strings.alternatives.launchConfigureSuffix}
              </p>
            )}
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}
