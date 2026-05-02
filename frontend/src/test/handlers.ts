import { setupServer } from 'msw/node'
import { http, HttpResponse } from 'msw'

export const baseHandlers = [
  http.get('/api/health', () =>
    HttpResponse.json({ status: 'ok' }, { status: 200 }),
  ),
]

export const server = setupServer(...baseHandlers)
export { http, HttpResponse }
