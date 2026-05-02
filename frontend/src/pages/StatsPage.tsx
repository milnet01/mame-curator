import { useId } from 'react'
import { strings } from '@/strings'
import type { Stats } from '@/api/types'

interface StatsPageProps {
  stats: Stats
}

function formatGB(bytes: number): string {
  return `${(bytes / 1024 ** 3).toFixed(1)} GB`
}

function topN(record: Record<string, number>, n = 10): [string, number][] {
  return Object.entries(record)
    .sort((a, b) => b[1] - a[1])
    .slice(0, n)
}

function StatsSection({
  title,
  data,
}: {
  title: string
  data: Record<string, number>
}) {
  const max = Math.max(1, ...Object.values(data))
  const entries = topN(data)
  // FP11 § H6: aria-labelledby links the section to its <h2> for AT.
  const headingId = useId()
  return (
    <section
      className="flex flex-col gap-2 rounded border bg-card p-3"
      aria-labelledby={headingId}
    >
      <h2 id={headingId} className="text-base font-semibold">
        {title}
      </h2>
      {entries.length === 0 ? (
        <p className="text-xs text-muted-foreground">No data yet.</p>
      ) : (
        <ul className="flex flex-col gap-1">
          {entries.map(([key, value]) => (
            <li key={key} className="grid grid-cols-[8rem_1fr_3rem] items-center gap-2 text-sm">
              <span className="truncate">{key}</span>
              <span
                className="h-3 rounded bg-primary"
                style={{ width: `${(value / max) * 100}%` }}
                aria-hidden="true"
              />
              <span className="text-right font-mono tabular-nums">{value}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export function StatsPage({ stats }: StatsPageProps) {
  return (
    <section className="flex flex-col gap-4 p-4">
      <header className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold">{strings.stats.pageTitle}</h1>
        <p className="text-sm text-muted-foreground">
          {strings.stats.totalSize(formatGB(stats.total_bytes))}
        </p>
      </header>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <StatsSection title={strings.stats.sections.genre} data={stats.by_genre} />
        <StatsSection title={strings.stats.sections.decade} data={stats.by_decade} />
        <StatsSection title={strings.stats.sections.publisher} data={stats.by_publisher} />
        <StatsSection title={strings.stats.sections.driverStatus} data={stats.by_driver_status} />
      </div>
    </section>
  )
}
