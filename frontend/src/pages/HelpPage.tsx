import { strings } from '@/strings'
import { cn } from '@/lib/utils'
import type { HelpTopic } from '@/api/types'

interface HelpPageProps {
  topics: HelpTopic[]
  selectedSlug: string | null
  topicHtml: string
  onSelect: (slug: string) => void
}

export function HelpPage({
  topics,
  selectedSlug,
  topicHtml,
  onSelect,
}: HelpPageProps) {
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
          {topics.map((t) => (
            <li key={t.slug}>
              <button
                type="button"
                onClick={() => onSelect(t.slug)}
                className={cn(
                  'w-full rounded px-2 py-1 text-left text-sm hover:bg-muted',
                  selectedSlug === t.slug && 'bg-muted font-semibold',
                )}
              >
                {t.title}
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <article className="prose prose-sm max-w-none dark:prose-invert">
        {/* Server returns rendered HTML per spec; no client-side markdown. */}
        {/* eslint-disable-next-line react/no-danger */}
        <div dangerouslySetInnerHTML={{ __html: topicHtml }} />
      </article>
    </section>
  )
}
