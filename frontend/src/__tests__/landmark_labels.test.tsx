/**
 * DS02 C4 — sibling-landmark aria-labels.
 *
 * Multiple `<aside>` / `<article>` landmarks render side-by-side on
 * the same page. Without aria-labels, AT users hear "complementary"
 * or "article" with no positional context, so cycling landmarks
 * (NVDA D / VO U) produces an undifferentiated list.
 *
 * Four sites need labels per spec:
 *  - `HelpPage.tsx` topic-list `<aside>` → "Help topics"
 *  - `HelpPage.tsx` rendered-topic `<article>` → "Help content"
 *  - `LibraryPage.tsx` FiltersSidebar `<aside>` → "Filters"
 *  - `CartPanel.tsx` cart contents `<aside>` → "Cart"
 *
 * Three are render-tested (HelpPage standalone, CartPanel
 * standalone — both prop-only and trivial to mount). LibraryPage
 * pulls in too many hooks for a unit render; its FiltersSidebar
 * `<aside>` is source-text-asserted instead, matching the existing
 * `DS02 C3` / `FP27 A6c` approach.
 *
 * Pre-fix: HelpPage's aside + article and FiltersSidebar's aside have
 * no aria-label. CartPanel has `aria-label={strings.library.cart.
 * contentsRegionLabel}` — the label value may or may not contain
 * "Cart" today, so the test asserts a future-stable "Cart"-ish label.
 */
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { HelpPage } from '../pages/HelpPage'
import { CartPanel } from '../components/library/CartPanel'
import libraryPageSource from '../pages/LibraryPage.tsx?raw'

describe('DS02 C4 — landmark aria-labels', () => {
  it('HelpPage topic-list aside carries aria-label "Help topics"', () => {
    render(
      <HelpPage
        topics={[{ slug: 't', title: 'Topic' }]}
        selectedSlug={null}
        topicHtml=""
        topicLoading={false}
        onSelect={() => {}}
      />,
    )
    // Use the implicit `complementary` role for <aside> with a name.
    const aside = screen.getByRole('complementary', { name: /help topics/i })
    expect(aside).toBeInTheDocument()
  })

  it('HelpPage rendered-topic article carries aria-label "Help content"', () => {
    render(
      <HelpPage
        topics={[{ slug: 't', title: 'Topic' }]}
        selectedSlug="t"
        topicHtml="<p>body</p>"
        topicLoading={false}
        onSelect={() => {}}
      />,
    )
    // <article> with an accessible name maps to role="article".
    const article = screen.getByRole('article', { name: /help content/i })
    expect(article).toBeInTheDocument()
  })

  it('CartPanel <aside> carries aria-label "Cart"', () => {
    render(
      <CartPanel
        open
        items={[]}
        onRemove={() => {}}
        onClearAll={() => {}}
      />,
    )
    // CartPanel renders <aside role="region">, so look up by region.
    const aside = screen.getByRole('region', { name: /^cart$/i })
    expect(aside).toBeInTheDocument()
  })

  it('LibraryPage FiltersSidebar <aside> source carries aria-label "Filters"', () => {
    // Source-text check — LibraryPage isn't worth a full render here,
    // and the `aria-label` is a static attribute on a JSX node. Allow
    // any quote style and any attribute order; require both that the
    // <aside> tag carries `aria-label` referencing "Filters" (literal
    // OR strings.<…>filtersLandmark / strings.<…>filters).
    const re =
      /<aside[^>]*\baria-label\s*=\s*(["'][^"']*[Ff]ilters[^"']*["']|\{[^}]*[Ff]ilters[^}]*\})[^>]*>/
    expect(
      re.test(libraryPageSource),
      'LibraryPage.tsx: no <aside aria-label="…Filters…"> found',
    ).toBe(true)
  })
})
