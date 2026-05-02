import { cn } from '@/lib/utils'
import { strings } from '@/strings'
import type { Explanation } from '@/api/types'

interface WhyPickedPanelProps {
  explanation: Explanation
}

export function WhyPickedPanel({ explanation }: WhyPickedPanelProps) {
  // Winner short_name is the explanation's `short_name` (the picked
  // child) or the parent itself in the no-clones case. Highlight it
  // in the candidates list per design §8.523 ("with current pick
  // highlighted").
  const winnerShortName = explanation.short_name

  return (
    <section className="flex flex-col gap-3 border-t pt-4">
      <header>
        <h3 className="text-sm font-semibold">
          {strings.alternatives.whyPickedTitle}
        </h3>
        <p className="text-xs text-muted-foreground">
          {strings.alternatives.whyPickedSubtitle}
        </p>
      </header>

      {explanation.hits.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          {strings.alternatives.whyPickedEmpty}
        </p>
      ) : (
        <ol className="flex flex-col gap-2 text-sm">
          {explanation.hits.map((hit, i) => (
            <li
              key={`${hit.name}-${i}`}
              className="flex flex-col rounded border bg-muted/40 px-3 py-2"
            >
              <span className="font-mono text-xs font-semibold uppercase text-muted-foreground">
                {hit.name}
              </span>
              <span>{hit.detail}</span>
            </li>
          ))}
        </ol>
      )}

      {explanation.candidates.length > 1 && (
        <p className="text-xs text-muted-foreground">
          <span className="mr-1">Candidates considered:</span>
          {explanation.candidates.map((name, i) => (
            <span key={name}>
              <span
                className={cn(
                  name === winnerShortName && 'font-semibold text-foreground',
                )}
                aria-current={name === winnerShortName ? 'true' : undefined}
              >
                {name}
              </span>
              {i < explanation.candidates.length - 1 && ', '}
            </span>
          ))}
        </p>
      )}
    </section>
  )
}
