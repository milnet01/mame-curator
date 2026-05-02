import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'

import { ActivityPage } from '../ActivityPage'

const items: Record<string, unknown>[] = [
  {
    timestamp: '2026-05-02T10:00:00Z',
    event_type: 'copy_finished',
    summary: 'Copied 42 games',
    session_id: 'sess-1',
  },
  {
    timestamp: '2026-05-02T09:00:00Z',
    event_type: 'override_set',
    summary: 'Override pacman → pacmanjr',
    session_id: 'sess-2',
  },
]

function renderAt(initialEntry: string, total = 150) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <ActivityPage pageSize={50} total={total} items={items} />
    </MemoryRouter>,
  )
}

describe('ActivityPage', () => {
  it('renders the paginated feed', () => {
    renderAt('/activity', 2)
    expect(screen.getByText(/Copied 42 games/)).toBeInTheDocument()
    expect(screen.getByText(/Override pacman/)).toBeInTheDocument()
  })

  it('reads the initial page from the URL ?page query (FP11 § B4)', () => {
    renderAt('/activity?page=3', 200)
    expect(screen.getByText(/Page 3 of/)).toBeInTheDocument()
  })

  it('writes ?page when the user clicks Next', async () => {
    renderAt('/activity?page=2', 200)
    await userEvent.click(screen.getByRole('button', { name: /next/i }))
    // Page indicator advances from 2 → 3.
    expect(screen.getByText(/Page 3 of/)).toBeInTheDocument()
  })

  it('renders an empty state when items is empty', () => {
    render(
      <MemoryRouter initialEntries={['/activity']}>
        <ActivityPage pageSize={50} total={0} items={[]} />
      </MemoryRouter>,
    )
    expect(screen.getByText(/no activity yet/i)).toBeInTheDocument()
  })
})
