/**
 * Fetch wrapper + typed error class for the MAME Curator API.
 *
 * - Every 2xx response with a body is validated against the caller's zod
 *   schema with `.strict()` mirroring Pydantic's `extra="forbid"`.
 * - 204 No Content is handled by `apiRequestVoid` (callers explicitly opt
 *   in to "expect no body"). The schema-bearing `apiRequest` does NOT
 *   accept 204 — it surfaces an `ApiError(code='response_unexpected_204')`
 *   so a route silently changing from 200 to 204 is caught.
 * - Every non-2xx response is decoded against `ApiErrorBodySchema` and
 *   re-thrown as `ApiError`. Fallback shapes:
 *     - network failure (no response)        → `code='network'`, `status=-1`
 *     - non-JSON body                        → `code='response_not_json'`
 *     - JSON but wrong schema (success path) → `code='response_shape_invalid'`
 *     - JSON but wrong error envelope        → `code='response_shape_invalid'`
 *   `status=-1` discriminates "never reached the wire" from "got a 200
 *   but body was wrong"; HTTP-status-bearing errors carry the real code.
 *
 * Per `docs/specs/P06.md` § "API contract surface" and FP11 § C4 + G4.
 */

import { z, type ZodType } from 'zod'
import {
  ApiErrorBodySchema,
  type ApiErrorBody,
  type FieldError,
} from './types'

/** Sentinel `status` value for failures that never reached the wire. */
export const STATUS_UNSENT = -1

export class ApiError extends Error {
  readonly code: string
  readonly detail: string
  readonly fields: FieldError[]
  readonly status: number

  constructor(body: ApiErrorBody, status: number, options?: { cause?: unknown }) {
    super(body.detail, options)
    this.name = 'ApiError'
    this.code = body.code
    this.detail = body.detail
    this.fields = body.fields
    this.status = status
  }
}

/**
 * Translate a zod error into the project's `FieldError[]` shape so
 * `validation_error` / `response_shape_invalid` toasts can highlight
 * the offending field. FP11 § G4: the prior implementation hard-coded
 * `fields: []`, throwing away zod's structured `.error.issues[]`.
 */
function fieldsFromZod(error: z.ZodError): FieldError[] {
  return error.issues.map((issue) => ({
    loc: issue.path.map(String).join('.'),
    msg: issue.message,
    type: issue.code,
  }))
}

/** Strict-parse a payload against a zod schema; throw `ApiError` on failure. */
export function parse<T>(schema: ZodType<T>, data: unknown): T {
  const result = schema.safeParse(data)
  if (!result.success) {
    throw new ApiError(
      {
        code: 'response_shape_invalid',
        detail: `response failed schema validation: ${z.prettifyError(result.error)}`,
        fields: fieldsFromZod(result.error),
      },
      STATUS_UNSENT,
    )
  }
  return result.data
}

interface RequestInitWithMethod extends Omit<RequestInit, 'method' | 'body'> {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
}

function buildRequest(
  init: RequestInitWithMethod,
): { method: string; headers: Headers; body: BodyInit | undefined; rest: RequestInit } {
  const { method = 'GET', body, headers: extraHeaders, ...rest } = init
  const headers = new Headers(extraHeaders)
  headers.set('Accept', 'application/json')
  let serializedBody: BodyInit | undefined
  if (body !== undefined) {
    headers.set('Content-Type', 'application/json')
    serializedBody = JSON.stringify(body)
  }
  return { method, headers, body: serializedBody, rest }
}

async function fetchOrThrow(path: string, init: RequestInit): Promise<Response> {
  try {
    return await fetch(path, init)
  } catch (err) {
    throw new ApiError(
      {
        code: 'network',
        detail: err instanceof Error ? err.message : 'network error',
        fields: [],
      },
      STATUS_UNSENT,
      { cause: err },
    )
  }
}

async function rejectIfErrorResponse(response: Response): Promise<void> {
  if (response.ok) return
  let payload: unknown
  try {
    payload = await response.json()
  } catch {
    throw new ApiError(
      {
        code: 'response_not_json',
        detail: `non-JSON response (status ${response.status})`,
        fields: [],
      },
      response.status,
    )
  }
  const errBody = ApiErrorBodySchema.safeParse(payload)
  if (!errBody.success) {
    throw new ApiError(
      {
        code: 'response_shape_invalid',
        detail: `unexpected error body shape (status ${response.status})`,
        fields: fieldsFromZod(errBody.error),
      },
      response.status,
    )
  }
  throw new ApiError(errBody.data, response.status)
}

/**
 * Issue an API request expecting a JSON body validated by `schema`.
 *
 * On 2xx with body: parse + return.
 * On 204: throw — use `apiRequestVoid` for body-less endpoints (R09 /
 *         R12 / R13b DELETE family). FP11 § C4: the prior implementation
 *         called `parse(schema, null)` for 204, but no zod schema accepts
 *         null, so every 204 call throws `response_shape_invalid` —
 *         silent contract failure for body-less endpoints. Now we surface
 *         the contract mismatch loudly.
 * On non-2xx: throw `ApiError` decoded from the typed envelope.
 * On network failure / non-JSON / shape-mismatch: typed `ApiError`.
 */
export async function apiRequest<T>(
  path: string,
  schema: ZodType<T>,
  init: RequestInitWithMethod = {},
): Promise<T> {
  const { method, headers, body, rest } = buildRequest(init)
  const response = await fetchOrThrow(path, { ...rest, method, headers, body })

  if (response.status === 204) {
    throw new ApiError(
      {
        code: 'response_unexpected_204',
        detail:
          'received 204 No Content for an endpoint expecting a JSON body — ' +
          'switch the caller to apiRequestVoid() if the route became body-less',
        fields: [],
      },
      response.status,
    )
  }

  await rejectIfErrorResponse(response)

  let payload: unknown
  try {
    payload = await response.json()
  } catch {
    throw new ApiError(
      {
        code: 'response_not_json',
        detail: `non-JSON response (status ${response.status})`,
        fields: [],
      },
      response.status,
    )
  }
  return parse(schema, payload)
}

/**
 * Issue an API request expecting an empty 204 No Content response.
 *
 * For the DELETE-style endpoints in the R09 / R12 / R13b family — the
 * server signals success via the status code alone, no body. Treats
 * 200 + empty body identically (some FastAPI handlers return 200 +
 * `null` JSON; both forms are ok). Anything else throws.
 */
export async function apiRequestVoid(
  path: string,
  init: RequestInitWithMethod = {},
): Promise<void> {
  const { method, headers, body, rest } = buildRequest(init)
  const response = await fetchOrThrow(path, { ...rest, method, headers, body })

  if (response.status === 204) return

  await rejectIfErrorResponse(response)

  // 2xx but not 204. Discard any body — caller asked for void.
  // (We don't fail on a non-empty body here; that would over-couple to
  // FastAPI's response-model autoflattening.)
}
