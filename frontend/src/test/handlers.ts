import { setupServer } from 'msw/node'
import { http, HttpResponse, type JsonBodyType } from 'msw'

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

/**
 * Build a ``GET /api/fs/list`` handler that returns ``homeListing`` for
 * the home path and an ``fs_sandboxed`` 403 for anything else.
 *
 * FP05 (2026-05-18) — five FsBrowser tests inlined the exact same
 * handler shape; extracted so the contract lives in one place. Callers
 * supply both ``home`` (the canonical home path) and ``homeListing``
 * (the JSON payload to return for it), keeping the helper free of
 * test-file globals.
 */
export function makeSandboxedListHandler(home: string, homeListing: JsonBodyType) {
  return http.get('/api/fs/list', ({ request }) => {
    const path = new URL(request.url).searchParams.get('path')
    if (path === home) return HttpResponse.json(homeListing)
    return HttpResponse.json(
      { code: 'fs_sandboxed', detail: `${path} outside allowlist`, fields: [] },
      { status: 403 },
    )
  })
}
