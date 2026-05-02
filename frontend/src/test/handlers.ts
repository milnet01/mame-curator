import { setupServer } from 'msw/node'
import { http, HttpResponse } from 'msw'

/**
 * MSW base handlers shared across the Vitest suite.
 *
 * Empty by design — the only handler we'd reach for would be
 * `/api/health`, but the backend doesn't define that route, and
 * frontend code never calls it (FP11 § I1: dead mock removed). Per-
 * test handlers are added with `server.use(...)` inside individual
 * test files when a route needs mocking.
 */
export const baseHandlers: Parameters<typeof setupServer> = []

export const server = setupServer(...baseHandlers)
export { http, HttpResponse }
