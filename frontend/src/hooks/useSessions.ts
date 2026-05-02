import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiRequest } from '@/api/client'
import {
  SessionsListingSchema,
  type Session,
  type SessionsListing,
} from '@/api/types'
import { useApiQuery } from './useApi'

const KEY = ['sessions'] as const

export function useSessions() {
  return useApiQuery<SessionsListing>(KEY, '/api/sessions', SessionsListingSchema)
}

function mutate(args: { method: 'POST' | 'DELETE'; path: string; body?: unknown }) {
  return apiRequest<SessionsListing>(args.path, SessionsListingSchema, {
    method: args.method,
    body: args.body,
  })
}

export function useSessionUpsert() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (args: { name: string; session: Session }) =>
      mutate({ method: 'POST', path: '/api/sessions', body: args }),
    onSuccess: (next) => qc.setQueryData(KEY, next),
  })
}

export function useSessionDelete() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (name: string) =>
      mutate({ method: 'DELETE', path: `/api/sessions/${encodeURIComponent(name)}` }),
    onSuccess: (next) => qc.setQueryData(KEY, next),
  })
}

export function useSessionActivate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (name: string) =>
      mutate({
        method: 'POST',
        path: `/api/sessions/${encodeURIComponent(name)}/activate`,
      }),
    onSuccess: (next) => qc.setQueryData(KEY, next),
  })
}

export function useSessionDeactivate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => mutate({ method: 'POST', path: '/api/sessions/_deactivate' }),
    onSuccess: (next) => qc.setQueryData(KEY, next),
  })
}
