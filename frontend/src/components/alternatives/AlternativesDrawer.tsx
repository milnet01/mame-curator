import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { strings } from '@/strings'
import type { GameCard } from '@/api/types'

interface AlternativesDrawerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  winner: GameCard
  alternatives: GameCard[]
  onOverride: (request: { parent: string; winner: string }) => void
}

export function AlternativesDrawer({
  open,
  onOpenChange,
  winner,
  alternatives,
  onOverride,
}: AlternativesDrawerProps) {
  const parent = winner.short_name
  const handleClick = (alt: GameCard) => {
    if (alt.short_name === winner.short_name) return
    onOverride({ parent, winner: alt.short_name })
    onOpenChange(false)
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="flex w-full max-w-md flex-col gap-4">
        <SheetHeader>
          <SheetTitle>{strings.alternatives.drawerTitle}</SheetTitle>
          <SheetDescription>
            {alternatives.length === 1
              ? strings.alternatives.emptyText
              : `${alternatives.length} versions in this family`}
          </SheetDescription>
        </SheetHeader>

        <ul className="flex flex-col gap-2">
          {alternatives.map((alt) => {
            const isWinner = alt.short_name === winner.short_name
            const buttonName = isWinner
              ? `${alt.description} — selected`
              : `Use ${alt.description}`
            return (
              <li key={alt.short_name}>
                <Card>
                  <CardContent className="flex items-center justify-between gap-3 p-3">
                    <div className="flex flex-col">
                      <span className="text-sm font-medium">
                        {alt.description}
                      </span>
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
                      onClick={() => handleClick(alt)}
                    >
                      {isWinner
                        ? strings.alternatives.pickedLabel
                        : strings.alternatives.overrideButton}
                    </Button>
                  </CardContent>
                </Card>
              </li>
            )
          })}
        </ul>
      </SheetContent>
    </Sheet>
  )
}
