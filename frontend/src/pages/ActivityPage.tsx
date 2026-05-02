import { useSearchParams } from 'react-router'
import { Button } from '@/components/ui/button'
import { strings } from '@/strings'

interface ActivityPageProps {
  /** Default page on first visit — the URL `?page` query param wins. */
  defaultPage?: number
  pageSize: number
  total: number
  items: Record<string, unknown>[]
}

const DEFAULT_PAGE = 1

export function ActivityPage({
  defaultPage = DEFAULT_PAGE,
  pageSize,
  total,
  items,
}: ActivityPageProps) {
  // FP11 § B4: spec § 191 binds "Pagination via `?page=N&page_size=50`
  // query params; URL state survives reload." `useSearchParams` reads
  // and writes the URL state directly so reload-survives-state works
  // without the parent threading callbacks.
  const [searchParams, setSearchParams] = useSearchParams()
  const parsedPage = Number(searchParams.get('page'))
  const page =
    Number.isInteger(parsedPage) && parsedPage > 0 ? parsedPage : defaultPage
  const onPageChange = (next: number) => {
    setSearchParams((prev) => {
      const out = new URLSearchParams(prev)
      out.set('page', String(next))
      out.set('page_size', String(pageSize))
      return out
    })
  }
  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  if (items.length === 0) {
    return (
      <section className="flex flex-col items-center gap-2 p-8 text-center">
        <h1 className="text-2xl font-semibold">{strings.activity.pageTitle}</h1>
        <p className="text-lg font-medium">{strings.activity.emptyTitle}</p>
        <p className="text-sm text-muted-foreground">{strings.activity.emptyHint}</p>
      </section>
    )
  }

  return (
    <section className="flex flex-col gap-4 p-4">
      <h1 className="text-2xl font-semibold">{strings.activity.pageTitle}</h1>

      <ul className="flex flex-col gap-2">
        {items.map((entry, i) => {
          // Note: React text-children escape HTML by default, so even
          // if `summary` ever carried `<script>...</script>`, it'd
          // render literally. The `String(...)` coercions also
          // narrow `unknown` for TS. If we ever switch to
          // `dangerouslySetInnerHTML` here (don't), we MUST sanitize.
          const timestamp = String(entry.timestamp ?? '')
          return (
            <li
              key={`${timestamp || i}-${i}`}
              className="flex flex-col rounded border bg-card px-3 py-2"
            >
              <span className="text-sm">{String(entry.summary ?? '')}</span>
              <span className="text-xs text-muted-foreground">
                {/* FP11 § H7: <time> for semantic timestamp markup. */}
                <time dateTime={timestamp}>{timestamp}</time>
                {' · '}
                {String(entry.event_type ?? '')}
              </span>
            </li>
          )
        })}
      </ul>

      <nav className="flex items-center justify-between gap-2">
        <Button
          variant="outline"
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
        >
          {strings.activity.pagination.prev}
        </Button>
        <span className="text-xs text-muted-foreground">
          {strings.activity.pagination.page(page, totalPages)}
        </span>
        <Button
          variant="outline"
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
        >
          {strings.activity.pagination.next}
        </Button>
      </nav>
    </section>
  )
}
