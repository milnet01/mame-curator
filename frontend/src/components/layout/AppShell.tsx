import { type ReactNode } from 'react'
import { NavLink } from 'react-router'
import { Activity, BarChart, BookOpen, Layers, Search, Settings } from 'lucide-react'
import { cn } from '@/lib/utils'
import { strings } from '@/strings'
import { Button } from '@/components/ui/button'

interface AppShellProps {
  children: ReactNode
  onCmdK: () => void
}

const NAV_ITEMS = [
  { to: '/', label: strings.nav.library, icon: Layers, end: true },
  { to: '/sessions', label: strings.nav.sessions, icon: Layers },
  { to: '/activity', label: strings.nav.activity, icon: Activity },
  { to: '/stats', label: strings.nav.stats, icon: BarChart },
  { to: '/settings', label: strings.nav.settings, icon: Settings },
  { to: '/help', label: strings.nav.help, icon: BookOpen },
]

export function AppShell({ children, onCmdK }: AppShellProps) {
  return (
    <div className="grid h-screen grid-cols-[14rem_1fr] grid-rows-[auto_1fr] bg-background text-foreground">
      <aside className="row-span-2 flex flex-col gap-3 border-r p-3">
        <header className="flex items-center justify-between px-1">
          <h1 className="text-lg font-semibold">{strings.app.name}</h1>
        </header>
        <nav className="flex flex-col gap-1 text-sm">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-2 rounded px-2 py-1.5 hover:bg-muted',
                  isActive && 'bg-muted font-medium',
                )
              }
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <header className="flex items-center justify-between border-b px-4 py-2">
        <Button variant="outline" size="sm" onClick={onCmdK} className="gap-2">
          <Search className="h-4 w-4" aria-hidden="true" />
          <span className="text-xs text-muted-foreground">
            {strings.nav.commandPalette}
          </span>
          <kbd className="ml-auto rounded border bg-muted px-1 py-0.5 text-[10px] font-mono">
            ⌘K
          </kbd>
        </Button>
      </header>

      <main className="overflow-auto">{children}</main>
    </div>
  )
}
