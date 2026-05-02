import { Button } from '@/components/ui/button'
import { strings } from '@/strings'

interface ActivityPageProps {
  page: number
  pageSize: number
  total: number
  items: Record<string, unknown>[]
  onPageChange: (page: number) => void
}

export function ActivityPage({
  page,
  pageSize,
  total,
  items,
  onPageChange,
}: ActivityPageProps) {
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
        {items.map((entry, i) => (
          <li
            key={`${entry.timestamp ?? i}-${i}`}
            className="flex flex-col rounded border bg-card px-3 py-2"
          >
            <span className="text-sm">{String(entry.summary ?? '')}</span>
            <span className="text-xs text-muted-foreground">
              {String(entry.timestamp ?? '')} · {String(entry.event_type ?? '')}
            </span>
          </li>
        ))}
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
