import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { http, HttpResponse, server } from '@/test/handlers'
import { ConfigureSourceKeyModal } from '../ConfigureSourceKeyModal'

function renderModal() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  const onOpenChange = vi.fn()
  render(
    <QueryClientProvider client={qc}>
      <ConfigureSourceKeyModal open onOpenChange={onOpenChange} sourceName="mobyGames" />
    </QueryClientProvider>,
  )
  return { qc, onOpenChange }
}

describe('ConfigureSourceKeyModal', () => {
  it('sends a PUT to the secret endpoint with the right body on save', async () => {
    const user = userEvent.setup()
    let captured: { name: unknown; body: unknown } | null = null
    server.use(
      http.put('/api/media/sources/:name/secret', async ({ request, params }) => {
        captured = { name: params.name, body: await request.json() }
        return new HttpResponse(null, { status: 204 })
      }),
    )
    renderModal()
    await user.type(screen.getByLabelText('API key'), 'my-key')
    await user.click(screen.getByRole('button', { name: /^save$/i }))
    await waitFor(() => expect(captured).not.toBeNull())
    expect(captured!.name).toBe('mobyGames')
    expect(captured!.body).toEqual({ secret: 'my-key' })
  })

  it('closes and invalidates the readiness query on 204', async () => {
    const user = userEvent.setup()
    server.use(
      http.put('/api/media/sources/:name/secret', () => new HttpResponse(null, { status: 204 })),
    )
    const { qc, onOpenChange } = renderModal()
    const invalidate = vi.spyOn(qc, 'invalidateQueries')
    await user.type(screen.getByLabelText('API key'), 'k')
    await user.click(screen.getByRole('button', { name: /^save$/i }))
    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false))
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['media', 'sources'] })
  })

  it('FP32 LOW: surfaces the ApiError detail (not a generic string) on 422', async () => {
    const user = userEvent.setup()
    server.use(
      http.put('/api/media/sources/:name/secret', () =>
        HttpResponse.json(
          { code: 'media_source_unknown', detail: 'No source named mobyGames.', fields: [] },
          { status: 422 },
        ),
      ),
    )
    renderModal()
    await user.type(screen.getByLabelText('API key'), 'bad')
    await user.click(screen.getByRole('button', { name: /^save$/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent('No source named mobyGames.')
  })

  it('FP32 LOW: clears the entered key when the modal is closed (defensive)', async () => {
    const user = userEvent.setup()
    function Harness() {
      const [open, setOpen] = useState(true)
      return (
        <>
          <button onClick={() => setOpen(true)}>reopen</button>
          <ConfigureSourceKeyModal open={open} onOpenChange={setOpen} sourceName="mobyGames" />
        </>
      )
    }
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    render(
      <QueryClientProvider client={qc}>
        <Harness />
      </QueryClientProvider>,
    )
    await user.type(screen.getByLabelText('API key'), 'secret-key')
    await user.click(screen.getByRole('button', { name: /cancel/i }))
    // Reopen: the field must be empty (the secret is not retained across close).
    await user.click(screen.getByRole('button', { name: /reopen/i }))
    expect(await screen.findByLabelText('API key')).toHaveValue('')
  })

  it('surfaces an inline error and stays open on 422', async () => {
    const user = userEvent.setup()
    server.use(
      http.put('/api/media/sources/:name/secret', () =>
        HttpResponse.json({ code: 'media_source_unknown', detail: 'bad', fields: [] }, { status: 422 }),
      ),
    )
    const { onOpenChange } = renderModal()
    await user.type(screen.getByLabelText('API key'), 'bad')
    await user.click(screen.getByRole('button', { name: /^save$/i }))
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
    expect(onOpenChange).not.toHaveBeenCalledWith(false)
  })
})
