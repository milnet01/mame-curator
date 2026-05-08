import { type ReactNode } from 'react'
import { NavLink } from 'react-router'
import {
  Activity,
  BarChart,
  BookOpen,
  Layers,
  MoreHorizontal,
  Search,
  Settings,
  ShoppingCart,
  type LucideIcon,
} from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { strings } from '@/strings'

interface AppShellProps {
  children: ReactNode
  cartCount: number
  onCmdK: () => void
  onOpenCart: () => void
}

interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  end?: boolean
}

const PRIMARY: NavItem[] = [
  { to: '/', label: strings.nav.library, icon: Layers, end: true },
  { to: '/settings', label: strings.nav.settings, icon: Settings },
  { to: '/help', label: strings.nav.help, icon: BookOpen },
]

const MORE: NavItem[] = [
  { to: '/sessions', label: strings.nav.sessions, icon: Layers },
  { to: '/activity', label: strings.nav.activity, icon: Activity },
  { to: '/stats', label: strings.nav.stats, icon: BarChart },
]

// FP24-C: the Cart entry was a NavLink to="/" so on Library it lit up
// active simultaneously with Library and clicking re-navigated home
// with no panel toggle. It is now a button that fires onOpenCart so
// the parent shell can open the cart panel from any route.
export function AppShell({ children, cartCount, onCmdK, onOpenCart }: AppShellProps) {
  return (
    <div className="grid h-screen grid-rows-[auto_1fr] bg-background text-foreground">
      <header className="flex items-center gap-4 border-b px-4 py-2">
        <h1 className="text-lg font-semibold">{strings.app.name}</h1>
        <nav className="flex items-center gap-1 text-sm">
          {PRIMARY.map(({ to, label, icon: Icon, end }) => (
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
          <button
            type="button"
            onClick={onOpenCart}
            className="flex items-center gap-2 rounded px-2 py-1.5 hover:bg-muted"
            aria-label={strings.nav.cart(cartCount)}
          >
            <ShoppingCart className="h-4 w-4" aria-hidden="true" />
            {cartCount}
          </button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                aria-label={strings.nav.more}
                className="gap-2"
              >
                <MoreHorizontal className="h-4 w-4" aria-hidden="true" />
                {strings.nav.more}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-48">
              {MORE.map(({ to, label, icon: Icon }) => (
                <DropdownMenuItem key={to} asChild>
                  <NavLink
                    to={to}
                    className={({ isActive }) =>
                      cn(
                        'flex items-center gap-2 rounded px-2 py-1.5',
                        isActive && 'bg-muted font-medium',
                      )
                    }
                  >
                    <Icon className="h-4 w-4" aria-hidden="true" />
                    {label}
                  </NavLink>
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </nav>
        <div className="ml-auto">
          <Button variant="outline" size="sm" onClick={onCmdK} className="gap-2">
            <Search className="h-4 w-4" aria-hidden="true" />
            <span className="text-xs text-muted-foreground">
              {strings.nav.commandPalette}
            </span>
            <kbd className="ml-auto rounded border bg-muted px-1 py-0.5 text-[10px] font-mono">
              {/* FP24-II: useKeyboard's `meta:true` matches Cmd on macOS,
                  Ctrl on Windows, Super on Linux. The kbd label adapts so
                  Linux/Windows users see "Ctrl+K" instead of the macOS
                  glyph for a key that doesn't fire the chord on their
                  platform. */}
              {typeof navigator !== 'undefined' && /Mac|iPhone|iPad/i.test(navigator.platform)
                ? '⌘K'
                : 'Ctrl+K'}
            </kbd>
          </Button>
        </div>
      </header>
      <main className="overflow-auto">{children}</main>
    </div>
  )
}
