import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

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

describe('ActivityPage', () => {
  it('renders the paginated feed', () => {
    render(
      <ActivityPage
        page={1}
        pageSize={50}
        total={2}
        items={items}
        onPageChange={() => {}}
      />,
    )
    expect(screen.getByText(/Copied 42 games/)).toBeInTheDocument()
    expect(screen.getByText(/Override pacman/)).toBeInTheDocument()
  })

  it('calls onPageChange when the user clicks Next', async () => {
    const onPageChange = vi.fn()
    render(
      <ActivityPage
        page={1}
        pageSize={50}
        total={150}
        items={items}
        onPageChange={onPageChange}
      />,
    )
    await userEvent.click(screen.getByRole('button', { name: /next/i }))
    expect(onPageChange).toHaveBeenCalledWith(2)
  })

  it('renders an empty state when items is empty', () => {
    render(
      <ActivityPage
        page={1}
        pageSize={50}
        total={0}
        items={[]}
        onPageChange={() => {}}
      />,
    )
    expect(screen.getByText(/no activity yet/i)).toBeInTheDocument()
  })
})
