import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
import type { ZodType } from 'zod'
import { apiRequest } from '@/api/client'

/**
 * Thin wrapper that turns an `apiRequest` call into a react-query query.
 * The schema is required so every cached response is validated; cache hits
 * skip re-validation since the parsed value already lived through it.
 */
export function useApiQuery<T>(
  key: readonly unknown[],
  url: string,
  schema: ZodType<T>,
  options?: Omit<
    UseQueryOptions<T, Error, T, readonly unknown[]>,
    'queryKey' | 'queryFn'
  >,
) {
  return useQuery({
    queryKey: key,
    queryFn: () => apiRequest(url, schema),
    staleTime: 30_000,
    ...options,
  })
}
