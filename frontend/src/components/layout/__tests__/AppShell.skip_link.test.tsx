/**
 * DS02 C1 — AppShell renders a "Skip to main content" link.
 *
 * a11y polish: keyboard users tabbing through the page hit a long
 * navbar before the first content control. The standard WCAG pattern
 * is a visually-hidden anchor at the top of the document that
 * focuses into the main landmark when activated.
 *
 * Contract:
 * - The skip-link is an `<a>` with `href="#main"` and visible text
 *   "Skip to main content".
 * - The corresponding `<main>` element exposes `id="main"` plus
 *   `tabIndex={-1}` so the anchor target is programmatically
 *   focusable (the negative tabindex keeps it out of the natural
 *   tab order while still being a valid focus target).
 * - The skip-link must precede the first interactive element of the
 *   header navigation, so the Tab key reaches it first.
 *
 * Pre-fix: AppShell has no skip-link; `<main>` has no `id` / `tabIndex`.
 * Post-fix: both assertions hold.
 */
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { AppShell } from '@/components/layout/AppShell'

function renderShell() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <AppShell cartCount={0} onCmdK={() => {}} onOpenCart={() => {}}>
        <div>content</div>
      </AppShell>
    </MemoryRouter>,
  )
}

describe('DS02 C1 — skip-to-main link', () => {
  it('renders an anchor with href="#main" and visible text', () => {
    renderShell()
    const link = screen.getByRole('link', { name: /skip to main content/i })
    expect(link.getAttribute('href')).toBe('#main')
  })

  it('skip-link is the FIRST element in tab order', () => {
    const { container } = renderShell()
    // First focusable in the rendered shell — link / button / [tabindex >= 0].
    const focusables = container.querySelectorAll<HTMLElement>(
      'a[href], button, [tabindex]:not([tabindex="-1"])',
    )
    expect(focusables.length).toBeGreaterThan(0)
    expect(focusables[0].textContent ?? '').toMatch(/skip to main content/i)
  })

  it('main landmark carries id="main" and tabIndex=-1', () => {
    renderShell()
    const main = screen.getByRole('main')
    expect(main.getAttribute('id')).toBe('main')
    expect(main.getAttribute('tabindex')).toBe('-1')
  })
})
