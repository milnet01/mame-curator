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

  it('strips <script> tags from topic html (P07 § D — DOMPurify)', () => {
    const malicious = '<p>Safe text</p><script>alert(1)</script>'
    const { container } = render(
      <HelpPage
        topics={topics}
        selectedSlug="overrides"
        topicHtml={malicious}
        onSelect={() => {}}
      />,
    )
    expect(screen.getByText(/Safe text/)).toBeInTheDocument()
    expect(container.querySelector('script')).toBeNull()
  })

  it('strips javascript: URLs from anchor hrefs (P07 § D — DOMPurify)', () => {
    const malicious = '<a href="javascript:alert(1)">click</a>'
    const { container } = render(
      <HelpPage
        topics={topics}
        selectedSlug="overrides"
        topicHtml={malicious}
        onSelect={() => {}}
      />,
    )
    const link = container.querySelector('a')
    const href = link?.getAttribute('href') ?? ''
    expect(href.toLowerCase()).not.toContain('javascript:')
  })

  // ---- FP20-L: DOMPurify config hardening ----------------------------------

  it('FP20-L: adds rel="noopener noreferrer" to target="_blank" links (reverse-tabnabbing)', () => {
    /**
     * Without ``rel="noopener"`` the new tab can navigate the opener
     * window (``window.opener.location = ...``) — the canonical
     * reverse-tabnabbing attack against external links. DOMPurify's
     * default profile leaves ``target="_blank"`` untouched; the
     * afterSanitizeAttributes hook closes the gap.
     */
    const html = '<a href="https://example.com" target="_blank">click</a>'
    const { container } = render(
      <HelpPage
        topics={topics}
        selectedSlug="overrides"
        topicHtml={html}
        onSelect={() => {}}
      />,
    )
    const link = container.querySelector('a')
    expect(link?.getAttribute('rel')).toBe('noopener noreferrer')
  })

  it('FP20-L: strips <style> tags (FORBID_TAGS)', () => {
    const html = '<p>text</p><style>body{color:red}</style>'
    const { container } = render(
      <HelpPage
        topics={topics}
        selectedSlug="overrides"
        topicHtml={html}
        onSelect={() => {}}
      />,
    )
    expect(container.querySelector('style')).toBeNull()
  })

  it('FP20-L: strips <form> tags (FORBID_TAGS — defends against credential-phishing inside help)', () => {
    const html = '<form action="/steal"><input name="x"/></form><p>after</p>'
    const { container } = render(
      <HelpPage
        topics={topics}
        selectedSlug="overrides"
        topicHtml={html}
        onSelect={() => {}}
      />,
    )
    expect(container.querySelector('form')).toBeNull()
    // The trailing <p> still renders — the strip is surgical.
    expect(screen.getByText('after')).toBeInTheDocument()
  })

  it('FP20-L: strips style="..." attributes (FORBID_ATTR — defense-in-depth against CSS-injection-based phishing)', () => {
    const html = '<p style="color:red; background:url(http://evil/track)">text</p>'
    const { container } = render(
      <HelpPage
        topics={topics}
        selectedSlug="overrides"
        topicHtml={html}
        onSelect={() => {}}
      />,
    )
    const p = container.querySelector('p')
    expect(p?.getAttribute('style')).toBeNull()
  })

  it('FP20-L: strips data: URLs on <img> (ALLOWED_URI_REGEXP — http/https/mailto only)', () => {
    const html = '<img src="data:image/png;base64,iVBORw0KGgo=" />'
    const { container } = render(
      <HelpPage
        topics={topics}
        selectedSlug="overrides"
        topicHtml={html}
        onSelect={() => {}}
      />,
    )
    const img = container.querySelector('img')
    // Either the img is removed entirely or its src is cleared — both
    // satisfy the security property (no data: payload survives).
    if (img !== null) {
      const src = img.getAttribute('src') ?? ''
      expect(src.toLowerCase()).not.toMatch(/^data:/)
    }
  })

  it('FP20-L: preserves https URLs on <a> (allowlist must not over-strip)', () => {
    const html = '<a href="https://example.com">click</a>'
    const { container } = render(
      <HelpPage
        topics={topics}
        selectedSlug="overrides"
        topicHtml={html}
        onSelect={() => {}}
      />,
    )
    const link = container.querySelector('a')
    expect(link?.getAttribute('href')).toBe('https://example.com')
  })

  it('FP20-L: preserves mailto: URLs (mailto is in the allowlist)', () => {
    const html = '<a href="mailto:hi@example.com">email</a>'
    const { container } = render(
      <HelpPage
        topics={topics}
        selectedSlug="overrides"
        topicHtml={html}
        onSelect={() => {}}
      />,
    )
    const link = container.querySelector('a')
    expect(link?.getAttribute('href')).toBe('mailto:hi@example.com')
  })
})
