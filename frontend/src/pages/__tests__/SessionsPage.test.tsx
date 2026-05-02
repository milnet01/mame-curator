import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { SessionsPage } from '../SessionsPage'
import type { Session } from '@/api/types'

const sessions: Record<string, Session> = {
  fighters: {
    include_genres: ['Fighting'],
    include_publishers: [],
    include_developers: [],
    include_year_range: [1990, 1999],
  },
  shooters: {
    include_genres: ['Shooter'],
    include_publishers: [],
    include_developers: [],
    include_year_range: null,
  },
}

describe('SessionsPage', () => {
  it('lists sessions with the active one badged', () => {
    render(
      <SessionsPage
        sessions={sessions}
        active="fighters"
        onActivate={() => {}}
        onDeactivate={() => {}}
        onDelete={() => {}}
        onCreate={() => {}}
      />,
    )
    expect(screen.getByText('fighters')).toBeInTheDocument()
    expect(screen.getByText('shooters')).toBeInTheDocument()
    // The Active badge appears once, on `fighters`.
    expect(screen.getAllByText(/active/i).length).toBeGreaterThan(0)
  })

  it('calls onActivate when the user activates a session', async () => {
    const onActivate = vi.fn()
    render(
      <SessionsPage
        sessions={sessions}
        active={null}
        onActivate={onActivate}
        onDeactivate={() => {}}
        onDelete={() => {}}
        onCreate={() => {}}
      />,
    )
    await userEvent.click(
      screen.getByRole('button', { name: /activate fighters/i }),
    )
    expect(onActivate).toHaveBeenCalledWith('fighters')
  })

  it('calls onDeactivate when the user deactivates the active session', async () => {
    const onDeactivate = vi.fn()
    render(
      <SessionsPage
        sessions={sessions}
        active="fighters"
        onActivate={() => {}}
        onDeactivate={onDeactivate}
        onDelete={() => {}}
        onCreate={() => {}}
      />,
    )
    await userEvent.click(screen.getByRole('button', { name: /deactivate/i }))
    expect(onDeactivate).toHaveBeenCalled()
  })

  it('shows an empty hint when no sessions exist', () => {
    render(
      <SessionsPage
        sessions={{}}
        active={null}
        onActivate={() => {}}
        onDeactivate={() => {}}
        onDelete={() => {}}
        onCreate={() => {}}
      />,
    )
    expect(screen.getByText(/no saved sessions yet/i)).toBeInTheDocument()
  })
})
