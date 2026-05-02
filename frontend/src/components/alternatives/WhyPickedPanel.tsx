import { strings } from '@/strings'
import type { Explanation } from '@/api/types'

interface WhyPickedPanelProps {
  explanation: Explanation
}

export function WhyPickedPanel({ explanation }: WhyPickedPanelProps) {
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
          No tiebreaker chain — only one candidate survived filtering.
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
          Candidates considered: {explanation.candidates.join(', ')}
        </p>
      )}
    </section>
  )
}
