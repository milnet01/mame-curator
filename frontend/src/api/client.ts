/**
 * Fetch wrapper + typed error class for the MAME Curator API.
 *
 * - Every successful response (2xx) is validated against the caller's zod
 *   schema with `.strict()` mirroring Pydantic's `extra="forbid"`.
 * - Every non-2xx response is decoded against `ApiErrorBodySchema` and
 *   re-thrown as `ApiError`. Fallback shapes (network errors, malformed
 *   bodies) raise `ApiError(code='internal', detail=<message>)`.
 *
 * Per `docs/specs/P06.md` § "API contract surface".
 */

import { z, type ZodType } from 'zod'
import {
  ApiErrorBodySchema,
  type ApiErrorBody,
  type FieldError,
} from './types'

export class ApiError extends Error {
  readonly code: string
  readonly detail: string
  readonly fields: FieldError[]
  readonly status: number

  constructor(body: ApiErrorBody, status: number) {
    super(body.detail)
    this.name = 'ApiError'
    this.code = body.code
    this.detail = body.detail
    this.fields = body.fields
    this.status = status
  }
}

/** Strict-parse a payload against a zod schema; rethrow on failure. */
export function parse<T>(schema: ZodType<T>, data: unknown): T {
  const result = schema.safeParse(data)
  if (!result.success) {
    throw new ApiError(
      {
        code: 'response_shape_invalid',
        detail: `response failed schema validation: ${z.prettifyError(result.error)}`,
        fields: [],
      },
      0,
    )
  }
  return result.data
}

interface RequestInitWithMethod extends Omit<RequestInit, 'method' | 'body'> {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
}

/**
 * Issue an API request and validate the response.
 *
 * Caller supplies a zod schema for the success body; on 2xx the parsed
 * value is returned. On non-2xx the body is parsed as `ApiErrorBody` and
 * thrown as `ApiError`. Network failures (offline, DNS, etc.) are wrapped
 * into `ApiError(code='network')`.
 */
export async function apiRequest<T>(
  path: string,
  schema: ZodType<T>,
  init: RequestInitWithMethod = {},
): Promise<T> {
  const { method = 'GET', body, headers: extraHeaders, ...rest } = init
  const headers = new Headers(extraHeaders)
  let serializedBody: BodyInit | undefined
  if (body !== undefined) {
    headers.set('Content-Type', 'application/json')
    serializedBody = JSON.stringify(body)
  }

  let response: Response
  try {
    response = await fetch(path, {
      ...rest,
      method,
      headers,
      body: serializedBody,
    })
  } catch (err) {
    throw new ApiError(
      {
        code: 'network',
        detail: err instanceof Error ? err.message : 'network error',
        fields: [],
      },
      0,
    )
  }

  if (response.status === 204) {
    return parse(schema, null)
  }

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

  if (!response.ok) {
    const errBody = ApiErrorBodySchema.safeParse(payload)
    if (!errBody.success) {
      throw new ApiError(
        {
          code: 'response_shape_invalid',
          detail: `unexpected error body shape (status ${response.status})`,
          fields: [],
        },
        response.status,
      )
    }
    throw new ApiError(errBody.data, response.status)
  }

  return parse(schema, payload)
}
