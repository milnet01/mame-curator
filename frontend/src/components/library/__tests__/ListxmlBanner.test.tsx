import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'

import { ListxmlBanner } from '../ListxmlBanner'

function renderBanner(props: { exists: boolean | undefined; cloneofMapSize?: number }) {
  return render(
    <MemoryRouter>
      <ListxmlBanner {...props} />
    </MemoryRouter>,
  )
}

describe('ListxmlBanner', () => {
  it('renders a warning when listxml is missing', () => {
    renderBanner({ exists: false })
    expect(screen.getByRole('alert')).toBeInTheDocument()
    // Banner names the file kind and the user-visible consequence so the
    // user can connect the symptom (duplicates) to the cause (no listxml).
    expect(screen.getByText(/listxml not configured/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /settings/i })).toHaveAttribute(
      'href',
      '/settings',
    )
  })

  it('does not render when listxml is fully loaded', () => {
    const { container } = renderBanner({ exists: true, cloneofMapSize: 27604 })
    expect(container).toBeEmptyDOMElement()
  })

  it('does not render while the setup-check is still loading (exists=undefined)', () => {
    const { container } = renderBanner({ exists: undefined })
    expect(container).toBeEmptyDOMElement()
  })

  it('renders empty-parse body when exists=true and cloneofMapSize=0', () => {
    renderBanner({ exists: true, cloneofMapSize: 0 })
    expect(
      screen.getByText(/Listxml loaded but contains no cloneof entries/i),
    ).toBeInTheDocument()
  })
})
