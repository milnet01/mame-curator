import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, renderHook, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'

import { http, HttpResponse, server } from '@/test/handlers'
import { useWikipediaExtract } from '@/hooks/useWikipediaExtract'
import { AboutSection } from '../AboutSection'

function makeClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } })
}

function wrapper(qc: QueryClient) {
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
}

const PAC = {
  title: 'Pac-Man',
  extract: 'Pac-Man is a 1980 maze arcade game.',
  url: 'https://en.wikipedia.org/wiki/Pac-Man',
  license: 'CC-BY-SA-4.0',
}

describe('useWikipediaExtract', () => {
  it('returns null on a 200 + null body (no wiki page)', async () => {
    server.use(http.get('/media/:name/wiki', () => HttpResponse.json(null)))
    const qc = makeClient()
    const { result } = renderHook(() => useWikipediaExtract('pacman'), { wrapper: wrapper(qc) })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toBeNull()
  })
})

describe('AboutSection', () => {
  function renderAbout() {
    return render(<AboutSection shortName="pacman" />, { wrapper: wrapper(makeClient()) })
  }

  it('renders nothing when there is no wiki page (null body)', async () => {
    server.use(http.get('/media/:name/wiki', () => HttpResponse.json(null)))
    const { container } = renderAbout()
    // Query settles to null; the section stays absent throughout.
    await waitFor(() => expect(container.firstChild).toBeNull())
    expect(container.firstChild).toBeNull()
  })

  it('renders the extract, a read-more link, and the license line on the happy path', async () => {
    server.use(http.get('/media/:name/wiki', () => HttpResponse.json(PAC)))
    renderAbout()
    expect(await screen.findByText(PAC.extract)).toBeInTheDocument()
    const link = screen.getByRole('link', { name: /read more/i })
    expect(link).toHaveAttribute('href', PAC.url)
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    expect(screen.getByText(/cc.by.sa/i)).toBeInTheDocument()
  })

  it('FP32 M2: drops the read-more link when the url is not https (keeps the text)', async () => {
    server.use(
      http.get('/media/:name/wiki', () =>
        HttpResponse.json({ ...PAC, url: 'javascript:alert(1)' }),
      ),
    )
    renderAbout()
    // The extract + license still render — only the unsafe link is dropped.
    expect(await screen.findByText(PAC.extract)).toBeInTheDocument()
    expect(screen.getByText(/cc.by.sa/i)).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /read more/i })).toBeNull()
  })

  it('renders nothing while loading (non-essential — no skeleton)', () => {
    server.use(http.get('/media/:name/wiki', () => new Promise(() => {})))
    const { container } = renderAbout()
    expect(container.firstChild).toBeNull()
  })
})
