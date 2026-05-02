import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

import { ErrorBoundary } from '../ErrorBoundary'

function Boom({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) throw new Error('kaboom')
  return <p>safe</p>
}

describe('ErrorBoundary', () => {
  it('renders children when no error is thrown', () => {
    render(
      <ErrorBoundary>
        <Boom shouldThrow={false} />
      </ErrorBoundary>,
    )
    expect(screen.getByText('safe')).toBeInTheDocument()
  })

  it('renders the fallback panel when a child throws', () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    render(
      <ErrorBoundary>
        <Boom shouldThrow />
      </ErrorBoundary>,
    )
    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByText('kaboom')).toBeInTheDocument()
    errorSpy.mockRestore()
  })

  it('clears the error when resetKey changes', () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const { rerender } = render(
      <ErrorBoundary resetKey="a">
        <Boom shouldThrow />
      </ErrorBoundary>,
    )
    expect(screen.getByRole('alert')).toBeInTheDocument()
    rerender(
      <ErrorBoundary resetKey="b">
        <Boom shouldThrow={false} />
      </ErrorBoundary>,
    )
    expect(screen.getByText('safe')).toBeInTheDocument()
    errorSpy.mockRestore()
  })

  it('exposes a Try again button in the fallback panel', () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    render(
      <ErrorBoundary>
        <Boom shouldThrow />
      </ErrorBoundary>,
    )
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
    errorSpy.mockRestore()
  })
})
