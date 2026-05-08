import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { AppShell } from '@/components/layout/AppShell'

function renderShell(
  props: Partial<React.ComponentProps<typeof AppShell>> = {},
  initialPath = '/',
) {
  const defaults: React.ComponentProps<typeof AppShell> = {
    children: <div>content</div>,
    cartCount: 0,
    onCmdK: () => {},
    onOpenCart: () => {},
  }
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <AppShell {...defaults} {...props} />
    </MemoryRouter>,
  )
}

describe('AppShell', () => {
  // FP24-C: the Cart entry in the navbar must NOT be a NavLink to "/" —
  // when it was, both Library and Cart highlighted simultaneously on
  // home and clicking re-navigated home with no panel toggle. The Cart
  // entry is now a button that fires onOpenCart().
  it('renders Cart as a button, not a navigation link', () => {
    renderShell({ cartCount: 3 })
    const cart = screen.getByRole('button', { name: /cart/i })
    expect(cart.tagName).toBe('BUTTON')
    expect(cart.getAttribute('href')).toBeNull()
  })

  it('fires onOpenCart when the Cart button is clicked', () => {
    const onOpenCart = vi.fn()
    renderShell({ cartCount: 0, onOpenCart })
    fireEvent.click(screen.getByRole('button', { name: /cart/i }))
    expect(onOpenCart).toHaveBeenCalledTimes(1)
  })

  it('Cart and Library do not both appear active on /', () => {
    renderShell({ cartCount: 1 }, '/')
    const library = screen.getByRole('link', { name: /library/i })
    expect(library.className).toMatch(/font-medium/)
    const cart = screen.getByRole('button', { name: /cart/i })
    // The Cart button must not pick up the active-style font-medium class.
    expect(cart.className).not.toMatch(/font-medium/)
  })
})
