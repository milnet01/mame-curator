import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { HelpPage } from '../HelpPage'
import type { HelpTopic } from '@/api/types'

const topics: HelpTopic[] = [
  { slug: 'getting-started', title: 'Getting started' },
  { slug: 'overrides', title: 'Manual overrides' },
]

describe('HelpPage', () => {
  it('lists topics from the index', () => {
    render(
      <HelpPage
        topics={topics}
        selectedSlug={null}
        topicHtml=""
        onSelect={() => {}}
      />,
    )
    expect(screen.getByText('Getting started')).toBeInTheDocument()
    expect(screen.getByText('Manual overrides')).toBeInTheDocument()
  })

  it('calls onSelect when a topic is clicked', async () => {
    const onSelect = vi.fn()
    render(
      <HelpPage
        topics={topics}
        selectedSlug={null}
        topicHtml=""
        onSelect={onSelect}
      />,
    )
    await userEvent.click(screen.getByText('Manual overrides'))
    expect(onSelect).toHaveBeenCalledWith('overrides')
  })

  it('renders the selected topic html', () => {
    render(
      <HelpPage
        topics={topics}
        selectedSlug="overrides"
        topicHtml="<p>How to override</p>"
        onSelect={() => {}}
      />,
    )
    expect(screen.getByText(/How to override/)).toBeInTheDocument()
  })

  it('shows the empty state when topics is empty', () => {
    render(
      <HelpPage
        topics={[]}
        selectedSlug={null}
        topicHtml=""
        onSelect={() => {}}
      />,
    )
    expect(screen.getByText(/no help topics/i)).toBeInTheDocument()
  })
})
