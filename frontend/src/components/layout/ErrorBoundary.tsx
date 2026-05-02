import { Component, type ErrorInfo, type ReactNode } from 'react'
import { strings } from '@/strings'

interface ErrorBoundaryProps {
  children: ReactNode
  /** Override the recoverable fallback panel. */
  fallback?: (error: Error, retry: () => void) => ReactNode
  /** Reset key — when this changes, the boundary clears its caught error. */
  resetKey?: unknown
}

interface ErrorBoundaryState {
  error: Error | null
}

/**
 * Catches render errors below it. Used at three nesting depths per spec:
 * - Route level (page crash → in-app fallback panel, sidebar still works).
 * - Drawer level (alternatives drawer crash → drawer body panel).
 * - Modal level (copy modal crash → modal body panel).
 *
 * Reset semantics: when `resetKey` changes (e.g. user navigates to a new
 * route, opens a different drawer), the boundary forgets the prior error
 * and retries rendering. There's also a manual "Try again" button.
 */
export class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { error: null }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error }
  }

  override componentDidUpdate(prev: ErrorBoundaryProps) {
    if (prev.resetKey !== this.props.resetKey && this.state.error !== null) {
      this.setState({ error: null })
    }
  }

  override componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary caught', error, info.componentStack)
  }

  retry = () => this.setState({ error: null })

  override render() {
    const { error } = this.state
    if (error) {
      if (this.props.fallback) return this.props.fallback(error, this.retry)
      return (
        <div
          role="alert"
          className="flex flex-col items-center gap-2 rounded border border-destructive/40 bg-destructive/10 p-4 text-sm"
        >
          <p className="font-semibold">{strings.errors.genericTitle}</p>
          <p className="text-xs text-muted-foreground">{error.message}</p>
          <button
            type="button"
            onClick={this.retry}
            className="rounded border bg-background px-3 py-1 text-xs hover:bg-muted"
          >
            Try again
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
