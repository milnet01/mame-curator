import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'

import { ListxmlBanner } from '../ListxmlBanner'

function renderInRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>)
}

describe('ListxmlBanner', () => {
  it('renders a warning when listxml is missing', () => {
    renderInRouter(<ListxmlBanner exists={false} />)
    expect(screen.getByRole('alert')).toBeInTheDocument()
    // Banner names the file kind and the user-visible consequence so the
    // user can connect the symptom (duplicates) to the cause (no listxml).
    expect(screen.getByText(/listxml not configured/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /settings/i })).toHaveAttribute(
      'href',
      '/settings',
    )
  })

  it('renders nothing when listxml exists', () => {
    const { container } = renderInRouter(<ListxmlBanner exists={true} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('renders nothing while the setup-check is still loading (exists=undefined)', () => {
    const { container } = renderInRouter(<ListxmlBanner exists={undefined} />)
    expect(container).toBeEmptyDOMElement()
  })
})
