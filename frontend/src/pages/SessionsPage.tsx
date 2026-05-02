import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { strings } from '@/strings'
import type { Session } from '@/api/types'

interface SessionsPageProps {
  sessions: Record<string, Session>
  active: string | null
  onActivate: (name: string) => void
  onDeactivate: () => void
  onDelete: (name: string) => void
  onCreate: () => void
}

function metaLine(session: Session): string {
  const labels = strings.sessions.metaLabels
  const yearLabel = session.include_year_range
    ? `${session.include_year_range[0]}–${session.include_year_range[1]}`
    : null
  return [
    session.include_genres.length
      ? `${labels.genres}: ${session.include_genres.join(', ')}`
      : null,
    session.include_publishers.length
      ? `${labels.publishers}: ${session.include_publishers.join(', ')}`
      : null,
    session.include_developers.length
      ? `${labels.developers}: ${session.include_developers.join(', ')}`
      : null,
    yearLabel ? `${labels.years}: ${yearLabel}` : null,
  ]
    .filter(Boolean)
    .join(strings.sessions.metaJoiner)
}

export function SessionsPage({
  sessions,
  active,
  onActivate,
  onDeactivate,
  onDelete,
  onCreate,
}: SessionsPageProps) {
  const names = Object.keys(sessions).sort()

  return (
    <section className="flex flex-col gap-4 p-4">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{strings.sessions.pageTitle}</h1>
        <div className="flex gap-2">
          {active !== null && (
            <Button variant="outline" onClick={onDeactivate}>
              {strings.sessions.actions.deactivate}
            </Button>
          )}
          <Button onClick={onCreate}>{strings.sessions.actions.newSession}</Button>
        </div>
      </header>

      {names.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded border bg-muted/30 p-8 text-center">
          <p className="text-lg font-medium">{strings.sessions.emptyTitle}</p>
          <p className="text-sm text-muted-foreground">{strings.sessions.emptyHint}</p>
        </div>
      ) : (
        <ul className="grid gap-3">
          {names.map((name) => {
            const isActive = name === active
            const session = sessions[name]!
            return (
              <li key={name}>
                <Card>
                  <CardHeader className="flex-row items-center justify-between gap-2">
                    <CardTitle className="flex items-center gap-2 text-base">
                      {name}
                      {isActive && (
                        <span className="rounded-full bg-primary px-2 py-0.5 text-xs font-medium text-primary-foreground">
                          {strings.sessions.activeBadge}
                        </span>
                      )}
                    </CardTitle>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onActivate(name)}
                        disabled={isActive}
                        aria-label={strings.sessions.actions.activateAriaLabel(name)}
                      >
                        {strings.sessions.actions.activate}
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => onDelete(name)}
                        aria-label={strings.sessions.actions.deleteAriaLabel(name)}
                      >
                        {strings.sessions.actions.delete}
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="text-xs text-muted-foreground">
                    {metaLine(session)}
                  </CardContent>
                </Card>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
